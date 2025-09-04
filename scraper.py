"""
Main scraper class for Urban Stems flower products.
"""

import asyncio
import time
import json
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Set, Optional
from playwright.async_api import async_playwright, Page, BrowserContext, Locator

from config import ScrapingConfig
from product_processor import add_product

logger = logging.getLogger(__name__)
      
class UrbanStemsScraper:
    def __init__(self, config: Optional[ScrapingConfig] = None):
        self.config = config or ScrapingConfig()
        self.products: List[Dict] = []
        self.variation_lookup: Dict = {}
        self.seen_cards: Set[str] = set()  # Track by product URL/ID to avoid duplicates
        self.discovered_categories: List[Dict[str, str]] = []
        self.discovered_collections: List[Dict[str, str]] = []
        self.discovered_occasions: List[Dict[str, str]] = []

        self.category_mapping: Dict[str, List[str]] = {}  # Track which categories each product appears in
        
    async def scrape(self) -> List[Dict]:
        """Main scraping method with category discovery"""
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
            await page.wait_for_selector("#products .product-card", timeout=15000, state="attached")
            
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
        total_items_processed = 0  # Track all items (new + existing)

        logger.info(f"📜 Starting to scrape '{page_name}' ({page_type}). Initial scroll height: {scroll_height}")

        # Start from the very top to ensure we don't miss any products
        await page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        await asyncio.sleep(1)

        while pos < scroll_height:
            # Scroll DOWN to the current position
            await self._scroll_to_position(page, pos)
            
            # Process visible cards after scrolling
            new_products_found = await self._process_visible_cards(page, context, page_slug, page_type, page_name)
            page_product_count += new_products_found
            total_items_processed += new_products_found
            
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

                # Generate a proper unique ID
                unique_id = f"{page_slug}_{product_id}_{len(self.products)}"

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
                    
                    # Initialize tracking for cross-page appearances
                    if product_id not in self.category_mapping:
                        self.category_mapping[product_id] = []
                    
                    # Add the appropriate attribute
                    if page_type == 'category':
                        self.category_mapping[product_id].append(page_name)
                    
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

    def _add_list_attribute(self, product: dict, attribute_name: str, value: str, emoji: str, update_mapping: bool = False, product_id: Optional[str] = None) -> None:
        """Generic method to add a value to a list attribute"""
        current_values = product.get(attribute_name, [])
        if isinstance(current_values, str):
            current_values = [current_values]
        
        if value not in current_values:
            current_values.append(value)
            product[attribute_name] = current_values
            
            # Update category mapping if needed
            if update_mapping and product_id and attribute_name == 'categories':
                if product_id in self.category_mapping:
                    self.category_mapping[product_id].append(value)
                else:
                    self.category_mapping[product_id] = current_values.copy()
            
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
                    'category': ('categories', '📂', True),
                    'collection': ('collections', '🏷️', False),
                    'occasion': ('occasions', '🎉', False)
                }
                
                if page_type in attribute_config:
                    attr_name, emoji, update_mapping = attribute_config[page_type]
                    self._add_list_attribute(existing_product, attr_name, page_name, emoji, update_mapping, product_id)
                        
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
        """Discover product categories from the main navigation"""
        page = None
        try:
            logger.info("🔍 Discovering product categories from navigation...")
            page = await context.new_page()
            
            # Navigate to main page
            await page.goto(self.config.category_discovery_url, wait_until="domcontentloaded")
            await asyncio.sleep(self.config.initial_wait)
            
            # Handle modal on main page first
            await self._handle_modal_popup(page)
            await self._hover_shop_nav_item(page)
        
        except Exception as e:
            logger.error(f"Category discovery failed: {e}")
            # Fallback
            self.discovered_categories = [
                {"name": "flowers", "url": f"{self.config.base_url}/collections/flowers", "category": "flowers"}
            ]
        finally:
            if page:
                await page.close()
            
    async def _hover_shop_nav_item(self, page: Page) -> None:
        """Hover over the Shop nav item to reveal dropdown"""
        try:
            nav_item = page.locator('div[data-nav-menu="shop"]').first
            if await nav_item.count() > 0:
                logger.info(f"🖱️ Hovering over Shop nav")
                
                # HOVER to reveal dropdown
                await nav_item.hover()
                await asyncio.sleep(2)  # Wait for dropdown to appear
                
                logger.info("✅ Shop dropdown should now be visible")
    
            try:
                # Look for category navigation links
                shop_type_selector = ".menu__col"
                
                # Wait for categories to be present (they might not be visible initially)
                await page.wait_for_selector(shop_type_selector, timeout=10000)
                
                # Get all category cards
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
                                    category_name = (await strong_element.inner_text()).strip().lower()
                                else:
                                    # No strong element, use the anchor tag's text
                                    category_name = (await field_card.inner_text()).strip().lower()
                                
                                if href and category_name:
                                    # Clean up category name (remove special chars, spaces)
                                    clean_category = category_name.replace(" ", "-").replace("&", "and")
                                    
                                    # Build full URL
                                    if href.startswith("/"):
                                        full_url = f"{self.config.base_url}{href}"
                                    else:
                                        full_url = href
                                    
                                    category_info = {
                                        "name": category_name,
                                        "url": full_url,
                                        "category": clean_category
                                    }
                                    
                                    if data_type == 'Categories':
                                        self.discovered_categories.append(category_info)
                                        logger.info(f"📂 Discovered category: {category_name} → {full_url}")
                                    if data_type == 'Featured':
                                        self.discovered_collections.append(category_info)
                                        logger.info(f"📂 Discovered collection: {category_name} → {full_url}")
                                    if data_type == 'Occasions':
                                        self.discovered_occasions.append(category_info)
                                        logger.info(f"📂 Discovered occasion: {category_name} → {full_url}")
                                
                            except Exception as e:
                                logger.warning(f"Failed to extract type info for {data_type}: {e}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to extract category info from card {i}: {e}")
                        continue
                
                if not self.discovered_categories:
                    logger.warning("No categories discovered, falling back to flowers")
                    self.discovered_categories = [{
                        "name": "flowers",
                        "url": f"{self.config.base_url}/collections/flowers", 
                        "category": "flowers"
                    }]
                else:
                    logger.info(f"✅ Discovered {len(self.discovered_categories)} categories")
                    
            except Exception as e:
                logger.error(f"Failed to find category navigation: {e}")
                # Fallback to default categories
                self.discovered_categories = [
                    {"name": "flowers", "url": f"{self.config.base_url}/collections/flowers", "category": "flowers"},
                    {"name": "plants", "url": f"{self.config.base_url}/collections/plants", "category": "plants"}
                ]
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
            await page.wait_for_selector(close_button_selector, timeout=8000)
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
        
        if abs(current_pos - position) < 50:  # Already close enough
            return
        
        # Perform the scroll
        await page.evaluate(f"window.scrollTo({{top: {position}, behavior: 'smooth'}})")
        
        # Wait for scroll to complete (with timeout)
        max_wait_time = 3.0  # 3 seconds max
        check_interval = 0.1  # Check every 100ms
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            await asyncio.sleep(check_interval)
            elapsed_time += check_interval
            
            new_pos = await page.evaluate("window.pageYOffset")
            if abs(new_pos - position) < 50:  # Close enough to target
                logger.debug(f"Scroll completed: {current_pos} → {new_pos} (target: {position})")
                break
        else:
            # If we exit the while loop due to timeout
            final_pos = await page.evaluate("window.pageYOffset")
            logger.warning(f"Scroll timeout: {current_pos} → {final_pos} (target: {position})")
        
        # Additional wait for any content that loads after scroll
        await asyncio.sleep(self.config.scroll_wait)

    def _add_category_to_existing_product(self, product_id: str, new_category: str) -> None:
        """Add a category to an existing product that appears in multiple categories"""
        try:
            # Find the existing product
            existing_product = None
            for product in self.products:
                if self._extract_product_id(product.get('url', '')) == product_id:  # Match by URL-based product ID
                    existing_product = product
                    break
            
            if existing_product:
                # Add category to the categories list
                current_categories = existing_product.get('categories', [existing_product.get('category')])
                if isinstance(current_categories, str):
                    current_categories = [current_categories]
                
                if new_category not in current_categories:
                    current_categories.append(new_category)
                    existing_product['categories'] = current_categories
                    
                    # Update category mapping
                    if product_id in self.category_mapping:
                        self.category_mapping[product_id].append(new_category)
                    else:
                        self.category_mapping[product_id] = current_categories.copy()
                    
                    logger.info(f"📂 Added category '{new_category}' to existing product: {existing_product.get('name')} (now in: {', '.join(current_categories)})")
                    
        except Exception as e:
            logger.warning(f"Failed to add category to existing product {product_id}: {e}")

    def _extract_product_id(self, href: str) -> str:
        """Extract product ID from href"""
        return urlparse(href).path.split("/")[-1]

    async def _save_results(self, duration: float) -> None:
        """Save results to JSON file with summary"""
        output_path = Path(self.config.output_file)
        
        try:
            with open(output_path, "w", encoding='utf-8') as f:
                json.dump(self.products, f, indent=2, ensure_ascii=False)
            
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
        
        # Count products by category (including cross-category products)
        category_counts = {}
        cross_category_products = 0
        
        for product in self.products:
            categories = product.get('categories', [product.get('category', 'unknown')])
            if isinstance(categories, str):
                categories = [categories]
            
            # Count cross-category products
            if len(categories) > 1:
                cross_category_products += 1
            
            # Count each category
            for category in categories:
                category_counts[category] = category_counts.get(category, 0) + 1
            
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
        logger.info(f"   - Cross-category products: {cross_category_products}")
        logger.info(f"   - Single products: {single_products}")
        logger.info(f"   - Variant products: {variant_products}")
        logger.info(f"   - Product families: {unique_families}")
        logger.info(f"   - Cross-referenced products: {cross_referenced}")
        
        # Log category breakdown (total appearances, not unique products)
        logger.info(f"   📂 Product appearances by category:")
        total_appearances = sum(category_counts.values())
        for category, count in sorted(category_counts.items()):
            percentage = (count / total_appearances * 100) if total_appearances > 0 else 0
            logger.info(f"      - {category}: {count} ({percentage:.1f}%)")
        
        # Log discovered categories
        if self.discovered_categories:
            logger.info(f"   🔍 Categories discovered:")
            for cat in self.discovered_categories:
                logger.info(f"      - {cat['name']} → {cat['url']}")
        
        # Log cross-category examples
        if cross_category_products > 0:
            logger.info(f"   🔄 Cross-category product examples:")
            examples_shown = 0
            for product in self.products:
                categories = product.get('categories', [])
                if isinstance(categories, list) and len(categories) > 1 and examples_shown < 3:
                    logger.info(f"      - '{product.get('name', 'Unknown')}' appears in: {', '.join(categories)}")
                    examples_shown += 1
        
        # Log some example variants if they exist
        if self.variation_lookup:
            example_family = next(iter(self.variation_lookup.keys()))
            variants = list(self.variation_lookup[example_family].keys())
            if len(variants) > 1:
                logger.info(f"   - Example family: '{example_family}' has variants: {variants}")

async def main():
    """Main entry point with configuration - kept for backward compatibility"""
    from config import ConfigPresets
    
    config = ConfigPresets.development()  # Use a preset for the standalone version
    
    scraper = UrbanStemsScraper(config)
    
    try:
        products = await scraper.scrape()
        logger.info(f"Scraping completed successfully with {len(products)} products")
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise

if __name__ == "__main__":
    # Configure basic logging for standalone execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(main())