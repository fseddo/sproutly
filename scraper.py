"""
Main scraper class for Urban Stems flower products.
"""

import asyncio
from enum import Enum
import time
import json
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Set, Optional, Dict
from playwright.async_api import async_playwright, Page, BrowserContext, Locator

from config import ScrapingConfig
from product_processor import add_product
from product_types import ProductList, AttributeList, VariationMapping, ProductDict, AttributeInfo, AttributeType
from constants import IGNORED_COLLECTIONS, SCROLL_CHECK_INTERVAL, SCROLL_MAX_WAIT_TIME, MODAL_WAIT_TIMEOUT, VIEWPORT_TOLERANCE

logger = logging.getLogger(__name__)
      
class UrbanStemsScraper:
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.products: ProductList = []
        self.variation_lookup: VariationMapping = {}
        self.seen_cards: Set[str] = set()  # Track by product URL/ID to avoid duplicates
        self.discovered_categories: AttributeList = []
        self.discovered_collections: AttributeList = []
        self.discovered_occasions: AttributeList = []

    def _add_discovered_attribute(self, data_type: str, name: str, url: str) -> None:
        """Add a discovered attribute (category, collection, or occasion) to the appropriate list"""
        # Filter out unwanted collections
        if data_type == 'Featured' and name in IGNORED_COLLECTIONS:
            logger.debug(f"Ignoring collection: {name}")
            return
            
        type_mapping: Dict[str, tuple[AttributeType, AttributeList]] = {
            'Categories': (AttributeType.CATEGORY, self.discovered_categories),
            'Featured': (AttributeType.COLLECTION, self.discovered_collections), 
            'Occasions': (AttributeType.OCCASION, self.discovered_occasions)
        }
        
        if data_type in type_mapping:
            attr_type, target_list = type_mapping[data_type]
            attribute_info: AttributeInfo = {
                "name": name,
                "url": url,
                "type": attr_type
            }
            target_list.append(attribute_info)
            logger.info(f"📂 Discovered {attr_type.value}: {name} → {url}")
        
    async def scrape(self) -> ProductList:
        """Main scraping method with attribute discovery"""
        start_time = time.time()
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.config.headless)
                context = await self._create_context(browser)

                # Discover pages for scraping
                await self._discover_pages(context)

                # Scrape item info from each page (categories, collections, occassions)
                await self._scrape_all_pages(context)
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise
        
        duration = time.time() - start_time
        await self._save_results(duration)
        return self.products

    async def _scrape_all_pages(self, context: BrowserContext) -> None:
        """Scrape products from all discovered categories, collections, and occasions"""
        
        # Apply page type limits before combining
        limited_categories = self.discovered_categories[:self.config.max_categories] if self.config.max_categories is not None else self.discovered_categories
        limited_collections = self.discovered_collections[:self.config.max_collections] if self.config.max_collections is not None else self.discovered_collections  
        limited_occasions = self.discovered_occasions[:self.config.max_occasions] if self.config.max_occasions is not None else self.discovered_occasions
        
        # Combine all page types into one list
        all_pages = [
            *[(info, 'category') for info in limited_categories],
            *[(info, 'collection') for info in limited_collections], 
            *[(info, 'occasion') for info in limited_occasions]
        ]
        
        total_pages = len(all_pages)
        logger.info(f"🎯 Starting to scrape {total_pages} pages:")
        logger.info(f"   - Categories: {len([p for p in all_pages if p[1] == 'category'])}")
        logger.info(f"   - Collections: {len([p for p in all_pages if p[1] == 'collection'])}")
        logger.info(f"   - Occasions: {len([p for p in all_pages if p[1] == 'occasion'])}")
        
        for i, (page_info, page_type) in enumerate(all_pages, 1):
            page_name = page_info["name"]
            page_url = page_info["url"]
            page_slug = page_info.get("category", page_info["name"].lower().replace(" ", "-"))
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📂 Scraping {page_type} {i}/{total_pages}: {page_name}")
            logger.info(f"🔗 URL: {page_url}")
            logger.info(f"{'='*60}")
            
            initial_product_count = len(self.products)
            
            try:
                await self._scrape_single_page(context, page_url, page_slug, page_type, page_name)
                
                page_product_count = len(self.products) - initial_product_count
                logger.info(f"✅ {page_type.title()} '{page_name}' complete: {page_product_count} products")
                
                # Check global product limit
                if self.config.max_products and len(self.products) >= self.config.max_products:
                    logger.info(f"🏁 Reached global product limit: {self.config.max_products}")
                    break
                    
            except Exception as e:
                logger.error(f"❌ Failed to scrape {page_type} '{page_name}': {e}")
                continue
        
        logger.info(f"\n🎉 All pages complete! Total products: {len(self.products)}")

    async def _scrape_single_page(self, context: BrowserContext, page_url: str, page_slug: str, page_type: str, page_name: str) -> None:
        """Scrape products from a single page (category, collection, or occasion)"""
        page = None
        try:
            page = await context.new_page()
            await self._setup_page(page, page_url, page_type, page_name)
            await self._scrape_products_from_page(page, context, page_slug, page_type, page_name)
            
        finally:
            if page:
                await page.close()

    async def _setup_page(self, page: Page, page_url: str, page_type: str, page_name: str) -> None:
        """Setup a page for scraping with unified logic"""
        logger.info(f"📄 Loading {page_type} page: {page_url}")
        await page.goto(page_url, wait_until="domcontentloaded")
        
        # Wait for initial content to load
        await asyncio.sleep(self.config.initial_wait)
        
        # Wait for product cards to be present in DOM (not necessarily visible)
        try:
            await page.wait_for_selector("#products .product-card", timeout=5000, state="attached")
            
            # Count total cards
            card_count = await page.locator("#products .product-card").count()
            logger.info(f"✅ Found {card_count} product cards on {page_type} page (will scroll to make them visible)")
            
            if card_count == 0:
                logger.warning(f"No product cards found on this {page_type} page")
                
        except Exception as e:
            logger.warning(f"⚠️ Product cards not found within timeout on {page_type} page: {e}")
            # Continue anyway - maybe they'll appear during scrolling

    async def _scrape_products_from_page(self, page: Page, context: BrowserContext, page_slug: str, page_type: str, page_name: str) -> None:
        """Scrape products from a single page with comprehensive scrolling"""
        scroll_step = self.config.scroll_step
        scroll_height = await page.evaluate("document.body.scrollHeight")
        pos = 0 
        page_product_count = 0

        logger.info(f"📜 Starting to scrape '{page_name}' ({page_type}). Initial scroll height: {scroll_height}")

        # Start from the very top to ensure we don't miss any products
        await page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        await asyncio.sleep(1)

        while pos < scroll_height:
            # Scroll DOWN to the current position
            await self._scroll_to_position(page, pos)
            
            # Process visible cards after scrolling
            new_products_found = await self._process_visible_cards(page, context, page_slug, page_type, page_name)
            
            # Check for early exit signal (no cards found)
            if new_products_found == -1:
                logger.info(f"🏁 No product cards found on '{page_name}' ({page_type}) - exiting early")
                break
                
            page_product_count += new_products_found
            
            if new_products_found > 0:
                logger.info(f"Found {new_products_found} new products in '{page_name}' ({page_type}) at scroll position {pos} (page total: {page_product_count})")
            else:
                logger.debug(f"No new products found at position {pos} (but may have processed existing products for tagging)")

            # Check category-specific product limit (only applies to categories)
            if (page_type == 'category' and self.config.max_products_per_category and 
                page_product_count >= self.config.max_products_per_category):
                logger.info(f"🏁 Reached category limit for '{page_name}': {self.config.max_products_per_category}")
                break
            
            # Check global product limit
            if self.config.max_products and len(self.products) >= self.config.max_products:
                logger.info(f"🏁 Reached global product limit: {self.config.max_products}")
                break

            # Check if products container is still in viewport
            try:
                products_container = page.locator("#products")
                if await products_container.count() > 0:
                    container_box = await products_container.bounding_box()
                    if container_box:
                        viewport_height = page.viewport_size['height'] if page.viewport_size else 800
                        # If the container is completely above the viewport, we've scrolled past it
                        if container_box['y'] + container_box['height'] < 0:
                            logger.info(f"🏁 Products container is out of view - stopping scroll at position {pos}")
                            break
            except Exception as e:
                logger.debug(f"Could not check products container visibility: {e}")

            # Check for more content (page might have grown)
            new_scroll_height = await page.evaluate("document.body.scrollHeight")
            if new_scroll_height > scroll_height:
                scroll_height = new_scroll_height
                logger.debug(f"Page height increased to: {scroll_height}")
            
            # Move to next scroll position (GOING DOWN THE PAGE)
            pos += scroll_step  # This should be positive to go down
            
            logger.debug(f"Next scroll position will be: {pos} (scroll_height: {scroll_height})")

        logger.info(f"✅ {page_type.title()} '{page_name}' scraping completed. New products found: {page_product_count}")

    async def _process_visible_cards(self, page: Page, context: BrowserContext, page_slug: str, page_type: str = "category", page_name: str = "unknown") -> int:
        """Process all visible product cards on current viewport with better visibility detection"""
        
        locator = page.locator("#products .product-card")
        count = await locator.count()
        new_products_count = 0

        logger.debug(f"Processing {count} product cards in {page_type} '{page_name}'")
        
        # If no cards found, return -1 to signal early exit
        if count == 0:
            logger.debug(f"No product cards found - signaling early exit")
            return -1

        for i in range(count):
            try:
                card = locator.nth(i)
                
                # Check if card is actually visible in viewport
                is_visible = await card.is_visible()
                if not is_visible:
                    continue
                
                # Additional check for viewport visibility
                try:
                    bounding_box = await card.bounding_box()
                    if not bounding_box:
                        continue
                    
                    # Check if at least part of the card is in viewport
                    viewport_size = page.viewport_size
                    if viewport_size and (bounding_box["y"] + bounding_box["height"] < 0 or 
                        bounding_box["y"] > viewport_size["height"]):
                        continue
                        
                except Exception:
                    # If bounding box check fails, continue with visibility check
                    pass
                
                if await self._process_single_card(card, i, context, page_slug, page_type, page_name):
                    new_products_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing card {i} in {page_type} '{page_name}': {e}")
                continue

        return new_products_count

    async def _process_single_card(self, card: Locator, index: int, context: BrowserContext, page_slug: str, page_type: str = "category", page_name: str = "unknown") -> bool:
        """Process a single product card with cross-page duplicate handling"""
        for attempt in range(self.config.max_retries):
            try:
                if not await card.is_visible():
                    return False

                await card.scroll_into_view_if_needed()

                # Extract product information for deduplication
                href = await card.locator("a.cover").get_attribute("href")
                if not href:
                    logger.warning(f"No href found for card {index} in {page_type} '{page_name}'")
                    return False

                product_id = self._extract_product_id(href)
                
                # Check if we've already processed this exact product
                if product_id in self.seen_cards:
                    logger.debug(f"Product {product_id} already exists - adding {page_type} '{page_name}'")
                    self._add_attribute_to_existing_product(product_id, page_type, page_name)
                    return False  # Don't count as new product, but attribute was added

                # Generate simple sequential ID
                unique_id = str(len(self.products))

                # Add product using function from product_processor
                product = await add_product(
                    product_locator=card,
                    idx=unique_id,
                    products=self.products,
                    variation_lookup=self.variation_lookup,
                    context=context,
                    category=page_slug,  # Keep this for backward compatibility
                    max_products=self.config.max_products
                )

                # Track this product regardless of success/failure to prevent reprocessing
                self.seen_cards.add(product_id)
                
                if product:
                    product_name = product.get('name', 'Unknown')
                    
                    # Initialize attributes for this product based on page type
                    product['categories'] = [page_slug] if page_type == 'category' else []
                    product['collections'] = [page_name] if page_type == 'collection' else []
                    product['occasions'] = [page_name] if page_type == 'occasion' else []
                       
                    logger.info(f"✅ Added [{page_type}] {product_id} - {product_name}")
                    
                    # Log variation info if applicable
                    if product.get('variant_type'):
                        base_name = product.get('base_name', 'Unknown')
                        variant_type = product.get('variant_type')
                        logger.debug(f"  └─ Variant: {base_name} ({variant_type})")
                    return True
                return False

            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    logger.error(f"Failed to process card {index} in '{page_name}' ({page_type}) after {self.config.max_retries} attempts: {e}")
                    return False
                else:
                    logger.warning(f"Attempt {attempt + 1} failed for card {index} in '{page_name}' ({page_type}): {e}. Retrying...")
                    await asyncio.sleep(1)
        return False

    def _add_list_attribute(self, product: ProductDict, attribute_name: str, value: str, emoji: str) -> None:
        """Generic method to add a value to a list attribute"""
        current_values = product.get(attribute_name, [])
        if isinstance(current_values, str):
            current_values = [current_values]
        
        if value not in current_values:
            current_values.append(value)
            product[attribute_name] = current_values
            logger.info(f"{emoji} Added {attribute_name[:-1]} '{value}' to existing product: {product.get('name')} (now in: {', '.join(current_values)})")

    def _add_attribute_to_existing_product(self, product_id: str, page_type: str, page_name: str) -> None:
        """Add a category, collection, or occasion to an existing product"""
        try:
            # Find the existing product
            existing_product = None
            for product in self.products:
                if self._extract_product_id(product.get('url', '')) == product_id:
                    existing_product = product
                    break
            
            if existing_product:
                attribute_config = {
                    'category': ('categories', '📂'),
                    'collection': ('collections', '🏷️'),
                    'occasion': ('occasions', '🎉')
                }
                
                if page_type in attribute_config:
                    attr_name, emoji = attribute_config[page_type]
                    self._add_list_attribute(existing_product, attr_name, page_name, emoji)
                        
        except Exception as e:
            logger.warning(f"Failed to add {page_type} to existing product {product_id}: {e}")

    async def _create_context(self, browser) -> BrowserContext:
        """Create browser context with proper viewport"""
        return await browser.new_context(
            viewport={
                "width": self.config.viewport_width, 
                "height": self.config.viewport_height
            }
        )

    async def _discover_pages(self, context: BrowserContext) -> None:
        """Discover product attributes from the main navigation"""
        page = None
        try:
            logger.info("🔍 Discovering product attributes from navigation...")
            page = await context.new_page()
            
            # Navigate to main page
            await page.goto(self.config.category_discovery_url, wait_until="domcontentloaded")
            await asyncio.sleep(self.config.initial_wait)
            
            # Handle modal on main page first
            await self._handle_modal_popup(page)
            await self._hover_shop_nav_item(page)
        
        except Exception as e:
            logger.error(f"Category discovery failed: {e}")
        finally:
            if page:
                await page.close()
            
    async def _hover_shop_nav_item(self, page: Page) -> None:
        """Hover over the Shop nav item to reveal dropdown"""
        try:
            nav_item = page.locator('div[data-nav-menu="shop"]').first
            if await nav_item.count() > 0:
                logger.info(f"🖱️ Hovering over Shop nav")
                
                # hover to reveal dropdown
                await nav_item.hover()
                await asyncio.sleep(2)  # Wait for dropdown to appear
                
                logger.info("✅ Shop dropdown should now be visible")
    
            try:
                # Look for attribute navigation links
                shop_type_selector = ".menu__col"
                
                # Wait for attributes to be present (they might not be visible initially)
                await page.wait_for_selector(shop_type_selector, timeout=10000)
                
                # Get all attribute cards
                shop_type_cards = page.locator(shop_type_selector)
                card_count = await shop_type_cards.count()
                
                logger.info(f"Found {card_count} shop type cards")
                
                for i in range(card_count):
                    try:
                        card = shop_type_cards.nth(i)
                        await asyncio.sleep(0.5)  # Small delay for visibility
                        
                        # Extract href and text
                        data_type = (await card.locator('strong.nav__menu-headline').first.inner_text()).strip()
                        type_fields = card.locator('a.hover-u')
                        type_fields_count = await type_fields.count()

                        logger.info(f"Found {type_fields_count} cards for {data_type}")
                        
                        for c in range(type_fields_count):
                            try:
                                field_card = type_fields.nth(c)
                                href = await field_card.get_attribute("href")
                                strong_element = field_card.locator('strong')
                                strong_count = await strong_element.count()
                                
                                if strong_count > 0:
                                    # Strong element exists, get its text
                                    attribute_name = (await strong_element.inner_text()).strip().lower()
                                else:
                                    # No strong element, use the anchor tag's text
                                    attribute_name = (await field_card.inner_text()).strip().lower()
                                
                                if href and attribute_name:                                 
                                    # Build full URL
                                    if href.startswith("/"):
                                        full_url = f"{self.config.base_url}{href}"
                                    else:
                                        full_url = href
                                    
                                    self._add_discovered_attribute(data_type, attribute_name, full_url)
                                
                            except Exception as e:
                                logger.warning(f"Failed to extract type info for {data_type}: {e}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to extract category info from card {i}: {e}")
                        continue

                logger.info(f"✅ Discovered {len(self.discovered_categories)} categories")
                    
            except Exception as e:
                logger.error(f"Failed to find category navigation: {e}")
                return
                
        except Exception as e:
            logger.warning("Could not find Shop nav item to hover over - trying fallback")
             # If hover fails, let's just proceed and see if categories are already visible
            logger.info("Proceeding without hover - categories might already be visible")
    


    async def _handle_modal_popup(self, page: Page) -> None:
        """Handle modal popups that might block content - AVOID SCROLLING"""
        logger.debug("Checking for modal popup...")
        close_button_selector = "button.big-close"
            
        try:
            # Wait for the modal close button to appear (with timeout)
            await page.wait_for_selector(close_button_selector, timeout=int(MODAL_WAIT_TIMEOUT * 1000))
            logger.info("Modal popup detected - attempting to close")
            
            # Use force click to avoid automatic scrolling
            await page.click(close_button_selector, force=True)
            logger.info("✅ Successfully closed modal popup")
            
            # Wait a moment for modal to disappear
            await asyncio.sleep(1)
            
            # Verify modal is gone by checking if close button is no longer visible
            try:
                is_visible = await page.is_visible(close_button_selector)
                if not is_visible:
                    logger.debug("Modal successfully dismissed")
                else:
                    logger.warning("Modal close button still visible after clicking")
            except Exception:
                logger.debug("Modal close button no longer exists (good)")
            
        except Exception as e:
            logger.debug("No modal popup detected or failed to close (this is often normal)")

    async def _scroll_to_position(self, page: Page, position: int) -> None:
        """Scroll to position with verification"""
        # Get current position before scrolling
        current_pos = await page.evaluate("window.pageYOffset")
        
        if abs(current_pos - position) < VIEWPORT_TOLERANCE:  # Already close enough
            return
        
        # Perform the scroll
        await page.evaluate(f"window.scrollTo({{top: {position}, behavior: 'smooth'}})")
        
        # Wait for scroll to complete (with timeout)
        max_wait_time = SCROLL_MAX_WAIT_TIME
        check_interval = SCROLL_CHECK_INTERVAL
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
            
            new_pos = await page.evaluate("window.pageYOffset")
            if abs(new_pos - position) < VIEWPORT_TOLERANCE:  # Close enough to target
                logger.debug(f"Scroll completed: {current_pos} → {new_pos} (target: {position})")
                break
        else:
            # If we exit the while loop due to timeout
            final_pos = await page.evaluate("window.pageYOffset")
            logger.warning(f"Scroll timeout: {current_pos} → {final_pos} (target: {position})")
        
        # Additional wait for any content that loads after scroll
        await asyncio.sleep(self.config.scroll_wait)


    def _extract_product_id(self, href: str) -> str:
        """Extract product ID from href"""
        return urlparse(href).path.split("/")[-1]

    def _enum_serializer(self, obj):
        if isinstance(obj, Enum):
            return obj.value 
        raise TypeError(f"Type {obj.__class__.__name__} not serializable")


    async def _save_results(self, duration: float) -> None:
        """Save results to JSON file with summary"""
        output_path = Path(self.config.output_file)
        
        try:
            with open(output_path, "w", encoding='utf-8') as f:
                json.dump(self.products, f, indent=2, ensure_ascii=False, default=self._enum_serializer)
            
            logger.info(f"✅ Scraped {len(self.products)} products and saved to '{output_path}'")
            logger.info(f"⏱️ Script finished in {duration:.2f} seconds.")
            
            # Log some statistics
            self._log_statistics()
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise

    def _log_statistics(self) -> None:
        """Log scraping statistics with category breakdown and cross-category analysis"""
        if not self.products:
            return
             
        # Count variations by analyzing variant types
        single_products = sum(1 for p in self.products if p.get('variant_type') is None)
        variant_products = len(self.products) - single_products
        
        # Count unique base names (product families)
        unique_families = len(self.variation_lookup)
        
        # Count products with cross-references to other variants
        cross_referenced = sum(1 for p in self.products 
                             if any(key.endswith('_variation') for key in p.keys()))
        
        logger.info(f"📊 Final Scraping Statistics:")
        logger.info(f"   - Total unique products: {len(self.products)}")
        logger.info(f"🔍 Discovery Summary:")
        logger.info(f"   - Categories: {len(self.discovered_categories)}")
        logger.info(f"   - Collections: {len(self.discovered_collections)}")
        logger.info(f"   - Occasions: {len(self.discovered_occasions)}")        
        logger.info(f"   - Single products: {single_products}")
        logger.info(f"   - Variant products: {variant_products}")
        logger.info(f"   - Product families: {unique_families}")
        logger.info(f"   - Cross-referenced products: {cross_referenced}")

