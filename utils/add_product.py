from bs4 import Tag
from playwright.sync_api import BrowserContext
from utils import get_item_badge, get_item_delivery_lead_time, get_item_detail_info, get_item_name, get_item_price, get_item_review_info, get_item_url, get_item_variant_type, get_image_src

BASE_URL = "https://urbanstems.com"

def add_product(tile: Tag, product_id, products, variation_lookup, context: BrowserContext, category: str):
    # if product_id > 3:
    #     return
    
    name = get_item_name(tile)
    product_url = get_item_url(tile, BASE_URL)
    delivery_lead_time = get_item_delivery_lead_time(tile)
    variant_type, base_name = get_item_variant_type(name)
    review_rating, review_count = get_item_review_info(tile)
    detail_info = get_item_detail_info(context, product_url, product_id)

    product = {
        "id": product_id,
        "name": name.strip(),
        "variant_type": variant_type if variant_type != "single" else None,
        "base_name": base_name,
        "url": product_url,
        "name": name,
        "price": get_item_price(tile, "span", "regular"),
        "discounted_price": get_item_price(tile, "s", "compare"),
        "main_image": get_image_src(tile, "main"),
        "hover_image": get_image_src(tile, "hover"),
        "badge_text": get_item_badge(tile),
        "delivery_lead_time": delivery_lead_time,
        "stock": 100 if delivery_lead_time else 0,
        "reviews_rating": review_rating,
        "reviews_count": review_count,
        "description": detail_info["description"] if detail_info else None,
        "care_instructions": detail_info["care_instructions"] if detail_info else None,
        "detail_image_1": detail_info["detail_image_1_src"] if detail_info else None,
        "detail_image_2": detail_info["detail_image_2_src"] if detail_info else None,
        "main_detail_src": detail_info["main_detail_src"] if detail_info else None,
        "is_main_detail_video": detail_info["is_main_detail_video"] if detail_info else None,
        "collection": None,
        "occasion": None,
        "category": category
    }

     # Add product to list
     # base name is The Verona even if double or triple
    products.append(product)
    # Ensure base entry exists
    if base_name not in variation_lookup:
        variation_lookup[base_name] = {}

    # Check if any other variations already exist
    existing_variants = variation_lookup[base_name]

    # Cross-reference other variants
    for other_variant, other_product in existing_variants.items():
        if other_variant != variant_type:
            #there is another variant
            product[f"{other_variant}_variation"] = other_product["id"]
            other_product[f"{variant_type}_variation"] = product_id
            products[other_product["id"]]

    # Add self-referencing field only if at least one other variant exists
    if any(v != variant_type for v in existing_variants):
        product[f"{variant_type}_variation"] = product_id

    # Update variation lookup
    variation_lookup[base_name][variant_type] = product

    return product