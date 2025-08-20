"""
Detail information extraction for Urban Stems products.

This module handles extracting detailed information from product detail pages,
including descriptions, care instructions, and images.
"""

import time
import logging
from typing import Optional, Dict, List, Any
from playwright.async_api import BrowserContext, TimeoutError, Page
from utils import get_item_description_info, scroll_and_extract

logger = logging.getLogger(__name__)

class DetailExtractionError(Exception):
    """Custom exception for detail extraction errors"""
    pass

class ProductDetailExtractor:
    """Handles extraction of detailed product information from product pages"""
    
    def __init__(self, timeout: int = 10000, max_scroll_attempts: int = 3):
        self.timeout = timeout
        self.max_scroll_attempts = max_scroll_attempts
        
    async def extract_accordion(self, card) -> Optional[Dict[str, str]]:
        """Extract accordion content (Description, Care Instructions, etc.)"""
        try:
            id_text = (await card.locator("summary").inner_text()).strip()
            if not id_text:
                return None
                
            content_locator = card.locator(".pdp__accordion-content")
            content = await get_item_description_info(content_locator, id_text)
            
            if content:
                logger.debug(f"Extracted accordion: {id_text}")
                return {"id": id_text, "content": content}
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract accordion: {e}")
            return None

    async def extract_image(self, card) -> Optional[Dict[str, str]]:
        """Extract image information from image cards"""
        try:
            img_src = await card.locator("img").get_attribute("src")
            if not img_src:
                return None
                
            alt_text = await card.locator("img").get_attribute("alt") or ""
            
            logger.debug(f"Extracted image: {img_src}")
            return {"id": img_src, "src": img_src, "alt": alt_text}
            
        except Exception as e:
            logger.warning(f"Failed to extract image: {e}")
            return None

    def get_extractors(self) -> List[Dict[str, Any]]:
        """Get the list of extractors for different content types"""
        return [
            {
                "name": "accordions",
                "locator_selector": ".pdp__accordion",
                "extract_func": self.extract_accordion
            },
            {
                "name": "images", 
                "locator_selector": ".image-card",
                "extract_func": self.extract_image
            }
        ]

    async def wait_for_page_ready(self, page: Page) -> bool:
        """Wait for the page to be ready for extraction"""
        try:
            # Wait for the main content selector
            await page.wait_for_selector(".pdp__accordion-content p", timeout=self.timeout)
            logger.debug("Page ready for extraction")
            return True
        except TimeoutError:
            logger.warning(f"Timeout waiting for page content (timeout: {self.timeout}ms)")
            return False

    async def extract_detail_content(self, page: Page) -> Dict[str, Any]:
        """Extract all detail content from the page"""
        try:
            extractors = self.get_extractors()
            results = await scroll_and_extract(page, extractors)
            
            accordions = results.get("accordions", [])
            images = results.get("images", [])
            
            # Extract specific content
            description = next(
                (item['content'] for item in accordions if item['id'] == "Description"), 
                None
            )
            care_instructions = next(
                (item['content'] for item in accordions if item['id'] == "Care Instructions"), 
                None
            )
            
            return {
                "description": description,
                "care_instructions": care_instructions,
                "accordions": accordions,
                "images": images,
                "total_accordions": len(accordions),
                "total_images": len(images)
            }
            
        except Exception as e:
            logger.error(f"Failed to extract detail content: {e}")
            raise DetailExtractionError(f"Content extraction failed: {e}")

    async def extract_product_details(
        self, 
        product_name: str, 
        product_url: Optional[str],  # Changed to Optional[str] to match the interface
        product_id: str,
        context: BrowserContext
    ) -> Optional[Dict[str, Any]]:
        """
        Extract detailed product information from a product page.
        
        Args:
            product_name: Name of the product (for logging)
            product_url: URL of the product detail page
            product_id: Unique identifier for the product (string type)
            context: Browser context for creating new pages
            
        Returns:
            Dictionary with extracted detail information or None if failed
        """
        if not product_url:
            logger.warning(f"Invalid product URL for '{product_name}' (ID: {product_id})")
            return None

        page = None
        start_time = time.time()
        
        try:
            logger.info(f"📦 Fetching details for '{product_name}' (ID: {product_id}) → {product_url}")
            
            # Create new page
            page = await context.new_page()
            
            # Navigate to product page
            await page.goto(product_url, wait_until="domcontentloaded")
            
            # Wait for page to be ready
            if not await self.wait_for_page_ready(page):
                logger.warning(f"Page not ready for '{product_name}' - proceeding anyway")
            
            # Extract content
            detail_content = await self.extract_detail_content(page)
            
            # Log success
            duration = time.time() - start_time
            logger.info(f"✅ Successfully extracted details for '{product_name}' in {duration:.2f}s")
            logger.debug(f"   - Description: {'✓' if detail_content.get('description') else '✗'}")
            logger.debug(f"   - Care Instructions: {'✓' if detail_content.get('care_instructions') else '✗'}")
            logger.debug(f"   - Total accordions: {detail_content.get('total_accordions', 0)}")
            logger.debug(f"   - Total images: {detail_content.get('total_images', 0)}")
            
            return {
                "description": detail_content.get("description"),
                "care_instructions": detail_content.get("care_instructions"),
                "extraction_time": duration,
                "extraction_success": True,
                # Future expansion - uncomment when needed
                # "detail_images": detail_content.get("images", []),
                # "all_accordions": detail_content.get("accordions", [])
            }
            
        except TimeoutError:
            duration = time.time() - start_time
            logger.error(f"❌ Timeout extracting details for '{product_name}' (ID: {product_id}) after {duration:.2f}s")
            return None
            
        except DetailExtractionError as e:
            duration = time.time() - start_time
            logger.error(f"❌ Detail extraction failed for '{product_name}' (ID: {product_id}): {e}")
            return None
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ Unexpected error extracting details for '{product_name}' (ID: {product_id}): {e}")
            return None
            
        finally:
            if page:
                try:
                    await page.close()
                    logger.debug(f"Closed page for '{product_name}'")
                except Exception as e:
                    logger.warning(f"Failed to close page for '{product_name}': {e}")

# Global extractor instance (can be configured)
_default_extractor = ProductDetailExtractor()

async def get_item_detail_info(
    name: str, 
    context: BrowserContext, 
    product_url: Optional[str], 
    product_id: str  # Changed from Optional[int] to str
) -> Optional[Dict[str, Any]]:
    """
    Compatibility function that maintains the original interface.
    
    This function bridges the old interface with the new class-based approach.
    
    Args:
        name: Product name
        context: Browser context
        product_url: Product detail page URL
        product_id: Product ID (now string instead of int)
        
    Returns:
        Dictionary with detail information or None if failed
    """
    if not product_url:
        logger.warning(f"⚠️ Invalid product link for item '{name}' (ID: {product_id})")
        return None
    
    return await _default_extractor.extract_product_details(
        product_name=name,
        product_url=product_url,
        product_id=product_id,
        context=context
    )

# Advanced function for custom configuration
async def get_item_detail_info_advanced(
    name: str,
    context: BrowserContext,
    product_url: Optional[str],
    product_id: str,
    timeout: int = 10000,
    max_scroll_attempts: int = 3
) -> Optional[Dict[str, Any]]:
    """
    Advanced version with configurable parameters.
    
    Args:
        name: Product name
        context: Browser context
        product_url: Product detail page URL
        product_id: Product ID
        timeout: Timeout in milliseconds for waiting for selectors
        max_scroll_attempts: Maximum number of scroll attempts
        
    Returns:
        Dictionary with detail information or None if failed
    """
    extractor = ProductDetailExtractor(timeout=timeout, max_scroll_attempts=max_scroll_attempts)
    
    return await extractor.extract_product_details(
        product_name=name,
        product_url=product_url,
        product_id=product_id,
        context=context
    )

# Batch processing function
async def extract_details_batch(
    products: List[Dict[str, Any]], 
    context: BrowserContext,
    max_concurrent: int = 3
) -> Dict[str, int]:
    """
    Extract details for multiple products with controlled concurrency.
    
    Args:
        products: List of product dictionaries with 'name', 'url', 'id' keys
        context: Browser context
        max_concurrent: Maximum number of concurrent extractions
        
    Returns:
        Statistics dictionary
    """
    import asyncio
    
    stats = {"total": len(products), "successful": 0, "failed": 0}
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def extract_single(product: Dict[str, Any]) -> bool:
        async with semaphore:
            result = await get_item_detail_info(
                name=product.get('name', 'Unknown'),
                context=context,
                product_url=product.get('url'),
                product_id=str(product.get('id', 'unknown'))
            )
            return result is not None
    
    tasks = [extract_single(product) for product in products]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            stats["failed"] += 1
        elif result:
            stats["successful"] += 1
        else:
            stats["failed"] += 1
    
    logger.info(f"Batch detail extraction complete: {stats}")
    return stats