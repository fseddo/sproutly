"""
Product extraction classes for Urban Stems scraper.

This module consolidates the utility functions into cohesive extractor classes.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Optional, Any, Tuple, List
from playwright.async_api import Locator, Page, BrowserContext

logger = logging.getLogger(__name__)

@asynccontextmanager
async def managed_page(context: BrowserContext, url: str, page_name: str):
    """Context manager for page lifecycle with automatic cleanup and error handling"""
    page = None
    try:
        logger.debug(f"📄 Opening page for {page_name}: {url}")
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        yield page
    except Exception as e:
        logger.error(f"❌ Error with page {page_name}: {e}")
        raise
    finally:
        if page:
            try:
                await page.close()
                logger.debug(f"🔒 Closed page for {page_name}")
            except Exception as e:
                logger.warning(f"Failed to close page for {page_name}: {e}")

class ProductTileExtractor:
    """Handles extraction of product information from product tiles"""
    
    @staticmethod
    async def extract_name(tile: Locator) -> Optional[str]:
        """Extract product name from tile"""
        try:
            name_locator = tile.locator(".product-card__title")
            if await name_locator.count() == 0:
                return None
            return await name_locator.inner_text()
        except Exception as e:
            logger.warning(f"Failed to extract name: {e}")
            return None

    @staticmethod
    async def extract_price(tile: Locator, element_name: str, modifier: str) -> Optional[int]:
        """Extract price from tile (returns price in cents as integer)"""
        try:
            price_locator = tile.locator(f"{element_name}[data-product-card-price-{modifier}]")
            if await price_locator.count() == 0:
                return None
                
            raw_text = (await price_locator.inner_text()).strip().replace("$", "")
            if not raw_text:
                return None
                
            try:
                # Convert to cents (multiply by 100 and convert to int)
                return int(float(raw_text) * 100)
            except ValueError:
                return None
        except Exception as e:
            logger.warning(f"Failed to extract {modifier} price: {e}")
            return None

    @staticmethod
    async def extract_image_src(tile: Locator, modifier: str) -> Optional[str]:
        """Extract image source from tile"""
        try:
            picture_tag = tile.locator(f"picture.product-card__media--{modifier}").first
            image_tag = picture_tag.locator("img").first

            if await image_tag.count() == 0:
                return None

            raw_src = await image_tag.get_attribute("src") or await image_tag.get_attribute("data-src")
            if not raw_src:
                return None
                
            if isinstance(raw_src, list) and raw_src:
                raw_src = raw_src[0]

            if isinstance(raw_src, str):
                image_src = raw_src.strip()
                if image_src.startswith("//"):
                    image_src = "https:" + image_src
                return image_src
            return None
        except Exception as e:
            logger.warning(f"Failed to extract {modifier} image: {e}")
            return None

    @staticmethod
    async def extract_badge(tile: Locator) -> Optional[str]:
        """Extract badge text from tile"""
        try:
            badge_locator = tile.locator(".badge")
            if await badge_locator.count() == 0:
                return None
            return (await badge_locator.inner_text()).strip()
        except Exception as e:
            logger.warning(f"Failed to extract badge: {e}")
            return None

    @staticmethod
    async def extract_url(tile: Locator, base_url: str) -> Optional[str]:
        """Extract product URL from tile"""
        try:
            link_locator = tile.locator("a.cover")
            if await link_locator.count() == 0:
                return None
                
            href = await link_locator.get_attribute("href")
            if not href:
                return None
                
            if href.startswith("/"):
                return f"{base_url}{href}"
            elif href.startswith("http"):
                return href
            return None
        except Exception as e:
            logger.warning(f"Failed to extract URL: {e}")
            return None

    @staticmethod
    async def extract_delivery_lead_time(tile: Locator) -> Optional[int]:
        """Extract delivery lead time from tile (returns days as integer)"""
        try:
            from datetime import date, datetime
            
            date_field = await tile.locator("time").get_attribute("datetime")
           
            if not date_field or date_field.lower() == "null":
                return None
            
            try:
                parsed_date = datetime.strptime(date_field, "%Y-%m-%d").date()
                return (parsed_date - date.today()).days
            except ValueError:
                return None
        except Exception as e:
            logger.warning(f"Failed to extract delivery time: {e}")
            return None

    @staticmethod
    async def extract_review_info(tile: Locator) -> Tuple[Optional[str], Optional[str]]:
        """Extract review rating and count from tile (returns as strings)"""
        try:
            review_rating = "0"
            review_count = "0"

            reviews_rating_locator = tile.locator(".rating-stars__icons")
            if await reviews_rating_locator.count() > 0:
                review_rating = await reviews_rating_locator.get_attribute("content") or "0"

            reviews_count_locator = tile.locator(".rating-stars__count")
            if await reviews_count_locator.count() > 0:
                review_count = await reviews_count_locator.get_attribute("content") or "0"

            return review_rating.strip(), review_count.strip()
        except Exception as e:
            logger.warning(f"Failed to extract review info: {e}")
            return "0", "0"

    @staticmethod
    def extract_variant_type(name: str) -> Tuple[str, str]:
        """Extract variant type and base name from product name"""
        if not name:
            return "single", name or ""
            
        name = name.strip()
        
        # Check for "Double" variant (name is already title-cased)
        if name.startswith("Double "):
            base_name = name[7:]  # Remove "Double "
            return "double", base_name
        
        if name.startswith("Triple "):
            base_name = name[7:]  # Remove "Triple "
            return "triple", base_name
        
        return "single", name

class ProductDetailContentExtractor:
    """Handles extraction of content information from product detail pages"""
    
    @staticmethod
    async def extract_description_info(tile: Locator, id_text: str) -> Optional[str]:
        """Extract description and care instructions from accordion content"""
        try:
            # Get all paragraphs within the accordion content
            paragraphs = await tile.locator("p").all()
            paragraph_htmls = []
            
            logger.debug(f"  ↪️ Accordion [{id_text}] contains {len(paragraphs)} paragraph(s)")
            
            for i, p in enumerate(paragraphs):
                html = await p.evaluate("(el) => el.outerHTML")
                paragraph_htmls.append(html)
                text = await p.text_content()
                snippet = text.strip()[:60] if text else ""
                logger.debug(f"    • Paragraph [{i}]: {snippet}")

            section_html = "".join(paragraph_htmls)

            if not section_html:
                logger.debug("  ⚠️ No product information found.")
                return None

            return section_html
            
        except Exception as e:
            logger.warning(f"Failed to extract description info for {id_text}: {e}")
            return None
    
    @staticmethod
    async def scroll_and_extract(
        page: Page,
        extractors: List[Dict[str, Any]],
        scroll_step: int = 80,
        scroll_pause: float = 2.0,
        max_scroll: Optional[int] = None
    ) -> Dict[str, List[Any]]:
        """Scroll through page and extract data using provided extractors"""
        try:
            # Prepare results dict and seen sets for deduplication
            results = {ex['name']: [] for ex in extractors}
            seen_ids = {ex['name']: set() for ex in extractors}

            scroll_height = await page.evaluate("document.body.scrollHeight")
            pos = 0

            while pos < scroll_height and (max_scroll is None or pos < max_scroll):
                await page.evaluate(f"window.scrollTo(0, {pos})")
                await asyncio.sleep(scroll_pause)

                for ex in extractors:
                    locator = page.locator(ex['locator_selector'])
                    count = await locator.count()

                    for i in range(count):
                        card = locator.nth(i)
                        try:
                            if not await card.is_visible():
                                continue
                            await card.scroll_into_view_if_needed()

                            data = await ex['extract_func'](card)
                            if data is None:
                                continue

                            data_id = data.get("id")
                            if data_id and data_id in seen_ids[ex['name']]:
                                continue
                            if data_id:
                                seen_ids[ex['name']].add(data_id)

                            results[ex['name']].append(data)

                        except Exception as e:
                            logger.warning(f"Error processing {ex['name']} element {i}: {e}")

                new_scroll_height = await page.evaluate("document.body.scrollHeight")
                if new_scroll_height == scroll_height:
                    break
                scroll_height = new_scroll_height
                pos += scroll_step

            return results
            
        except Exception as e:
            logger.error(f"Failed to scroll and extract: {e}")
            return {ex['name']: [] for ex in extractors}

class ProductDetailMediaExtractor:
    """Handles extraction of media information from product detail pages"""
    
    @staticmethod
    async def extract_media_info(page: Page) -> Optional[Dict[str, Any]]:
        """Extract media information (images and videos) from product detail page"""
        try:
            lifestyle_items = page.locator(".pdp__lifestyle-grid figure")
            item_count = await lifestyle_items.count()
            
            if item_count == 0:
                logger.debug("⚠️ No lifestyle media found.")
                return None

            main_detail_src = None
            is_main_detail_video = False
            detail_image_1_src = None
            detail_image_2_src = None

            logger.debug(f"🎞 Found {item_count} lifestyle media item(s)")

            for idx in range(item_count):
                item = lifestyle_items.nth(idx)
                
                # Try to get video first (priority over images)
                video_locator = item.locator("video")
                if await video_locator.count() > 0 and not main_detail_src:
                    video_src = await video_locator.get_attribute("data-in-view-video-src")
                    if video_src:
                        video_src = video_src.strip()
                        if video_src.startswith("//"):
                            video_src = "https:" + video_src
                        main_detail_src = video_src
                        is_main_detail_video = True
                        logger.debug(f"  ▶️ Video found: {video_src}")

                # Try to get image from picture
                picture_locator = item.locator("picture").first
                if await picture_locator.count() > 0:
                    img_locator = picture_locator.locator("img")
                    if await img_locator.count() > 0:
                        img_src = await img_locator.get_attribute("src")
                        if img_src:
                            img_src = img_src.strip()
                            if img_src.startswith("//"):
                                img_src = "https:" + img_src

                            # Assign based on index and priority
                            if idx == 0 and not main_detail_src:
                                main_detail_src = img_src
                                logger.debug(f"  🖼 Main Detail Image: {img_src}")
                            elif idx == 1:
                                detail_image_1_src = img_src
                                logger.debug(f"  🖼 Detail Image 1: {img_src}")
                            elif idx == 2:
                                detail_image_2_src = img_src
                                logger.debug(f"  🖼 Detail Image 2: {img_src}")

            return {
                "main_detail_src": main_detail_src, 
                "is_main_detail_video": is_main_detail_video, 
                "detail_image_1_src": detail_image_1_src, 
                "detail_image_2_src": detail_image_2_src
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract media info: {e}")
            return None