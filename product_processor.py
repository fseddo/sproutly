"""
Product Processing Module for Urban Stems Scraper

This module handles the extraction and processing of product data from
Urban Stems product tiles, including variation linking logic.
"""

import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import BrowserContext, Locator
from extraction_utils import ProductTileExtractor
from product_detail_extractor import get_item_detail_info

logger = logging.getLogger(__name__)

BASE_URL = "https://urbanstems.com"

class ProductExtractionError(Exception):
    """Custom exception for product extraction errors"""
    pass

class ProductProcessor:
    """Handles product processing with better error handling and validation"""
    
    @staticmethod
    def find_existing_product(products: List[Dict[str, Any]], name: str, url: Optional[str] = None) -> Optional[Dict[str, Any]]:
     """Find existing product by name or URL"""
     for product in products:
         if product['name'] == name or (url and product['url'] == url):
             return product
     return None

    @staticmethod
    def update_product_tags(
      product: Dict[str, Any], 
      category: Optional[str] = None,
      collection: Optional[str] = None, 
      occasion: Optional[str] = None
    ) -> None:
      """Update product tags by appending to existing arrays"""
      if category and category not in product['categories']:
          product['categories'].append(category)

      if collection and collection not in product['collections']:
          product['collections'].append(collection)

      if occasion and occasion not in product['occasions']:
          product['occasions'].append(occasion)

    @staticmethod
    async def extract_basic_info(tile) -> Dict[str, Any]:
        """Extract basic product information from tile"""
        try:
            name = await ProductTileExtractor.extract_name(tile)
            if not name:
                raise ProductExtractionError("Product name is empty")
            
            # Normalize name to title case for consistency
            name = name.strip().title()
                
            variant_type, base_name = ProductTileExtractor.extract_variant_type(name)
            review_rating_str, review_count_str = await ProductTileExtractor.extract_review_info(tile)
            
            # Convert string ratings to appropriate types
            review_rating = None
            review_count = None
            
            if review_rating_str and review_rating_str != "0":
                try:
                    review_rating = float(review_rating_str)
                except ValueError:
                    review_rating = None
                    
            if review_count_str and review_count_str != "0":
                try:
                    review_count = int(review_count_str)
                except ValueError:
                    review_count = None
            
            return {
                'name': name.strip(),
                'variant_type': variant_type,
                'base_name': base_name.strip() if base_name else name.strip(),
                'review_rating': review_rating,
                'review_count': review_count
            }
        except Exception as e:
            logger.error(f"Failed to extract basic info: {e}")
            raise ProductExtractionError(f"Basic info extraction failed: {e}")

    @staticmethod
    async def extract_image_info(tile) -> Dict[str, Optional[str]]:
        """Extract image information with fallback handling"""
        try:
            return {
                'main_image': await ProductTileExtractor.extract_image_src(tile, "main"),
                'hover_image': await ProductTileExtractor.extract_image_src(tile, "hover")
            }
        except Exception as e:
            logger.warning(f"Failed to extract image info: {e}")
            return {'main_image': None, 'hover_image': None}

    @staticmethod
    async def extract_pricing_info(tile) -> Dict[str, Optional[int]]:
        """Extract pricing information with validation (prices in cents)"""
        try:
            return {
                'price': await ProductTileExtractor.extract_price(tile, "span", "regular"),
                'discounted_price': await ProductTileExtractor.extract_price(tile, "s", "compare")
            }
        except Exception as e:
            logger.warning(f"Failed to extract pricing info: {e}")
            return {'price': None, 'discounted_price': None}

    @staticmethod
    async def extract_additional_info(tile) -> Dict[str, Any]:
        """Extract additional product information"""
        try:
            delivery_lead_time = await ProductTileExtractor.extract_delivery_lead_time(tile)
            return {
                'badge_text': await ProductTileExtractor.extract_badge(tile),
                'product_url': await ProductTileExtractor.extract_url(tile, BASE_URL),
                'delivery_lead_time': delivery_lead_time,
                'stock': 100 if delivery_lead_time else 0 
            }
        except Exception as e:
            logger.warning(f"Failed to extract additional info: {e}")
            return {
                'badge_text': None,
                'product_url': None,
                'delivery_lead_time': None,
                'stock': 0
            }

def create_product_object(
    product_id: str,
    basic_info: Dict[str, Any],
    image_info: Dict[str, Optional[str]],
    pricing_info: Dict[str, Optional[int]],
    additional_info: Dict[str, Any],
    detail_info: Optional[Dict[str, Any]],
    category: Optional[str] = None,
    collection: Optional[str] = None,
    occasion: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a standardized product object"""
    
    return {
        "id": product_id,
        "name": basic_info['name'],
        "variant_type": basic_info['variant_type'] if basic_info['variant_type'] != "single" else None,
        "base_name": basic_info['base_name'],
        "url": additional_info['product_url'],
        "price": pricing_info['price'],
        "discounted_price": pricing_info['discounted_price'],
        "main_image": image_info['main_image'],
        "hover_image": image_info['hover_image'],
        "badge_text": additional_info['badge_text'],
        "delivery_lead_time": additional_info['delivery_lead_time'],
        "stock": additional_info['stock'],
        "reviews_rating": basic_info['review_rating'],
        "reviews_count": basic_info['review_count'],
        "description": detail_info.get("description") if detail_info else None,
        "care_instructions": detail_info.get("care_instructions") if detail_info else None,
        "main_detail_src": detail_info.get("media_info", {}).get("main_detail_src") if detail_info and detail_info.get("media_info") else None,
        "is_main_detail_video": detail_info.get("media_info", {}).get("is_main_detail_video") if detail_info and detail_info.get("media_info") else False,
        "detail_image_1_src": detail_info.get("media_info", {}).get("detail_image_1_src") if detail_info and detail_info.get("media_info") else None,
        "detail_image_2_src": detail_info.get("media_info", {}).get("detail_image_2_src") if detail_info and detail_info.get("media_info") else None,
        "collections": [collection] if collection else [],
        "occasions": [occasion] if occasion else [],
        "categories": [category] if category else [],
    }

def link_product_variations(
    product: Dict[str, Any], 
    variant_type: str, 
    base_name: str, 
    variation_lookup: Dict[str, Dict[str, Any]]
) -> None:
    """
    Link product variations together with cross-references.
    
    This creates bidirectional links between product variants like:
    - "The Margot" and "Double the Margot"
    - Each variant gets fields like "double_variation" pointing to the other's ID
    """
    
    # Initialize base name entry if it doesn't exist
    if base_name not in variation_lookup:
        variation_lookup[base_name] = {}
    
    existing_variants = variation_lookup[base_name]
    product_id = product["id"]
    
    # Cross-reference with existing variants
    linked_count = 0
    for other_variant_type, other_product in existing_variants.items():
        if other_variant_type != variant_type:
            # Link current product to other variant
            product[f"{other_variant_type}_variation"] = other_product["id"]
            # Link other product to current variant
            other_product[f"{variant_type}_variation"] = product_id
            linked_count += 1
            
            logger.debug(f"Linked '{product['name']}' ({variant_type}) with '{other_product['name']}' ({other_variant_type})")
    
    # Add self-reference if other variants exist
    if existing_variants and any(v != variant_type for v in existing_variants):
        product[f"{variant_type}_variation"] = product_id
    
    # Update the lookup table
    variation_lookup[base_name][variant_type] = product
    
    # After adding this product to the lookup, check if we now have multiple variants
    all_variants = variation_lookup[base_name]
    if len(all_variants) > 1:  # Multiple variants exist for this base name
        for var_type, var_product in all_variants.items():
            # If this is a "single" variant but variant_type is None, update it
            if var_type == "single" and var_product.get("variant_type") is None:
                var_product["variant_type"] = "single"
                logger.debug(f"Updated variant_type to 'single' for base product: {var_product['name']}")
    
    if linked_count > 0:
        logger.info(f"Product '{product['name']}' linked to {linked_count} variant(s)")

async def add_product(
    product_locator: Locator,
    idx: str,
    products: List[Dict[str, Any]],
    variation_lookup: Dict[str, Dict[str, Any]],
    context: BrowserContext,
    category: str,
    max_products: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Add a product to the products list with variation linking.
    
    Args:
        product_locator: Locator tied to product from Playwright
        idx: Unique identifier for the product
        products: List to add the product to
        variation_lookup: Dictionary tracking product variations
        context: Browser context for detail scraping
        category: Product category (e.g., 'flower')
        max_products: Optional limit on products to process
    
    Returns:
        The created product dict or None if failed/skipped
    """
    
    # Check product limit
    if max_products and len(products) >= max_products:
        logger.info(f"Reached maximum product limit: {max_products}")
        return None
    
    try:
        # Extract all product information with error handling
        logger.debug(f"Processing product {idx}")
        
        basic_info = await ProductProcessor.extract_basic_info(product_locator)
        image_info = await ProductProcessor.extract_image_info(product_locator)
        pricing_info = await ProductProcessor.extract_pricing_info(product_locator)
        additional_info = await ProductProcessor.extract_additional_info(product_locator)
        
        # Validate essential information
        if not basic_info['name']:
            logger.warning(f"Skipping product {idx}: No name found")
            return None
            
        if not additional_info['product_url']:
            logger.warning(f"Skipping product {idx}: No URL found")
            return None
        
        # Get detailed information (optional, with timeout protection)
        detail_info = None
        try:
            detail_info = await get_item_detail_info(
                basic_info['name'], 
                context, 
                additional_info['product_url'], 
                idx
            )
            logger.debug(f"Successfully extracted detail info for {basic_info['name']}")
        except Exception as e:
            logger.warning(f"Failed to get detail info for '{basic_info['name']}': {e}")
            # Continue without detail info rather than failing entirely
        
        # Create product object
        product = create_product_object(
            product_id=idx,
            basic_info=basic_info,
            image_info=image_info,
            pricing_info=pricing_info,
            additional_info=additional_info,
            detail_info=detail_info,
            category=category
        )
        
        # Add to products list
        products.append(product)
        
        # Handle variation linking
        link_product_variations(
            product, 
            basic_info['variant_type'], 
            basic_info['base_name'], 
            variation_lookup
        )
        
        logger.info(f"Successfully added product: '{basic_info['name']}' (ID: {idx})")
        return product
        
    except ProductExtractionError as e:
        logger.error(f"Product extraction failed for {idx}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error adding product {idx}: {e}")
        return None
