# import logging
# from typing import Dict, List, Optional, Tuple, Any
# from playwright.async_api import BrowserContext
# from utils import (
#     get_item_badge, get_item_delivery_lead_time, get_item_detail_info, 
#     get_item_name, get_item_price, get_item_review_info, get_item_url, 
#     get_item_variant_type, get_image_src
# )

# logger = logging.getLogger(__name__)

# BASE_URL = "https://urbanstems.com"

# class ProductProcessor:
#     """Handles product processing with better error handling and validation"""
    
#     @staticmethod
#     async def extract_basic_info(tile) -> Dict[str, Any]:
#         """Extract basic product information from tile"""
#         try:
#             name = await get_item_name(tile)
#             variant_type, base_name = get_item_variant_type(name)
#             review_rating, review_count = await get_item_review_info(tile)
            
#             return {
#                 'name': name,
#                 'variant_type': variant_type,
#                 'base_name': base_name,
#                 'review_rating': review_rating,
#                 'review_count': review_count
#             }
#         except Exception as e:
#             logger.error(f"Failed to extract basic info: {e}")
#             raise

#     @staticmethod
#     async def extract_image_info(tile) -> Dict[str, Optional[str]]:
#         """Extract image information"""
#         try:
#             return {
#                 'main_image': await get_image_src(tile, "main"),
#                 'hover_image': await get_image_src(tile, "hover")
#             }
#         except Exception as e:
#             logger.warning(f"Failed to extract image info: {e}")
#             return {'main_image': None, 'hover_image': None}

#     @staticmethod
#     async def extract_pricing_info(tile) -> Dict[str, Optional[float]]:
#         """Extract pricing information"""
#         try:
#             return {
#                 'price': await get_item_price(tile, "span", "regular"),
#                 'discounted_price': await get_item_price(tile, "s", "compare")
#             }
#         except Exception as e:
#             logger.warning(f"Failed to extract pricing info: {e}")
#             return {'price': None, 'discounted_price': None}

#     @staticmethod
#     async def extract_additional_info(tile) -> Dict[str, Any]:
#         """Extract additional product information"""
#         try:
#             badge_text = await get_item_badge(tile)
#             product_url = await get_item_url(tile, BASE_URL)
#             delivery_lead_time = await get_item_delivery_lead_time(tile)
            
#             return {
#                 'badge_text': badge_text,
#                 'product_url': product_url,
#                 'delivery_lead_time': delivery_lead_time,
#                 'stock': 100 if delivery_lead_time else 0
#             }
#         except Exception as e:
#             logger.warning(f"Failed to extract additional info: {e}")
#             return {
#                 'badge_text': None,
#                 'product_url': None,
#                 'delivery_lead_time': None,
#                 'stock': 0
#             }

# def create_product_object(
#     product_id: str,
#     basic_info: Dict[str, Any],
#     image_info: Dict[str, Optional[str]],
#     pricing_info: Dict[str, Optional[float]],
#     additional_info: Dict[str, Any],
#     detail_info: Optional[Dict[str, Any]],
#     category: str
# ) -> Dict[str, Any]:
#     """Create a standardized product object"""
    
#     return {
#         "id": product_id,
#         "name": basic_info['name'],
#         "variant_type": basic_info['variant_type'] if basic_info['variant_type'] != "single" else None,
#         "base_name": basic_info['base_name'],
#         "url": additional_info['product_url'],
#         "price": pricing_info['price'],
#         "discounted_price": pricing_info['discounted_price'],
#         "main_image": image_info['main_image'],
#         "hover_image": image_info['hover_image'],
#         "badge_text": additional_info['badge_text'],
#         "delivery_lead_time": additional_info['delivery_lead_time'],
#         "stock": additional_info['stock'],
#         "reviews_rating": basic_info['review_rating'],
#         "reviews_count": basic_info['review_count'],
#         "description": detail_info.get("description") if detail_info else None,
#         "care_instructions": detail_info.get("care_instructions") if detail_info else None,
#         "collection": None,
#         "occasion": None,
#         "category": category
#     }

# def link_product_variations(
#     product: Dict[str, Any], 
#     variant_type: str, 
#     base_name: str, 
#     variation_lookup: Dict[str, Dict[str, Any]]
# ) -> None:
#     """Link product variations together with cross-references"""
    
#     # Initialize base name entry if it doesn't exist
#     if base_name not in variation_lookup:
#         variation_lookup[base_name] = {}
    
#     existing_variants = variation_lookup[base_name]
#     product_id = product["id"]
    
#     # Cross-reference with existing variants
#     for other_variant_type, other_product in existing_variants.items():
#         if other_variant_type != variant_type:
#             # Link current product to other variant
#             product[f"{other_variant_type}_variation"] = other_product["id"]
#             # Link other product to current variant
#             other_product[f"{variant_type}_variation"] = product_id
            
#             logger.debug(f"Linked {product['name']} with {other_product['name']}")
    
#     # Add self-reference if other variants exist
#     if any(v != variant_type for v in existing_variants):
#         product[f"{variant_type}_variation"] = product_id
    
#     # Update the lookup table
#     variation_lookup[base_name][variant_type] = product

# async def add_product(
#     tile,
#     idx: str,  # Changed to string for better ID management
#     products: List[Dict[str, Any]],
#     variation_lookup: Dict[str, Dict[str, Any]],
#     context: BrowserContext,
#     category: str,
#     max_products: Optional[int] = None  # Made configurable
# ) -> Optional[Dict[str, Any]]:
#     """
#     Add a product to the products list with variation linking.
    
#     Args:
#         tile: The product tile element
#         idx: Unique identifier for the product
#         products: List to add the product to
#         variation_lookup: Dictionary tracking product variations
#         context: Browser context for detail scraping
#         category: Product category
#         max_products: Optional limit on products to process
    
#     Returns:
#         The created product dict or None if failed/skipped
#     """
    
#     # Optional early exit for testing/debugging
#     if max_products and len(products) >= max_products:
#         logger.info(f"Reached maximum product limit: {max_products}")
#         return None
    
#     try:
#         # Extract all product information
#         basic_info = await ProductProcessor.extract_basic_info(tile)
#         image_info = await ProductProcessor.extract_image_info(tile)
#         pricing_info = await ProductProcessor.extract_pricing_info(tile)
#         additional_info = await ProductProcessor.extract_additional_info(tile)
        
#         # Get detailed information (this might fail, so make it optional)
#         detail_info = None
#         try:
#             detail_info = await get_item_detail_info(
#                 basic_info['name'], 
#                 context, 
#                 additional_info['product_url'], 
#                 idx
#             )
#         except Exception as e:
#             logger.warning(f"Failed to get detail info for {basic_info['name']}: {e}")
        
#         # Create product object
#         product = create_product_object(
#             product_id=idx,
#             basic_info=basic_info,
#             image_info=image_info,
#             pricing_info=pricing_info,
#             additional_info=additional_info,
#             detail_info=detail_info,
#             category=category
#         )
        
#         # Add to products list
#         products.append(product)
        
#         # Handle variation linking
#         link_product_variations(
#             product, 
#             basic_info['variant_type'], 
#             basic_info['base_name'], 
#             variation_lookup
#         )
        
#         logger.debug(f"Successfully processed product: {basic_info['name']}")
#         return product
        
#     except Exception as e:
#         logger.error(f"Failed to add product at index {idx}: {e}")
#         return None

# # Alternative function for batch processing with better error handling
# async def add_product_batch(
#     tiles: List[Any],
#     products: List[Dict[str, Any]],
#     variation_lookup: Dict[str, Dict[str, Any]],
#     context: BrowserContext,
#     category: str,
#     start_idx: int = 0
# ) -> Tuple[int, int]:
#     """
#     Process multiple product tiles in batch with comprehensive error handling.
    
#     Returns:
#         Tuple of (successful_count, failed_count)
#     """
#     successful = 0
#     failed = 0
    
#     for i, tile in enumerate(tiles):
#         try:
#             product_id = f"{category}_{start_idx + i}"
#             result = await add_product(tile, product_id, products, variation_lookup, context, category)
#             if result:
#                 successful += 1
#             else:
#                 failed += 1
#         except Exception as e:
#             logger.error(f"Batch processing failed for tile {i}: {e}")
#             failed += 1
    
#     logger.info(f"Batch processing complete: {successful} successful, {failed} failed")
#     return successful, failed