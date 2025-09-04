"""
CSS Selectors for Urban Stems Scraper

This module centralizes all CSS selectors used throughout the scraper
to improve maintainability and avoid duplication.
"""

# Product Card Selectors
PRODUCT_CARD = "#products .product-card"
PRODUCT_CARD_TITLE = ".product-card__title"
PRODUCT_CARD_MEDIA_MAIN = "picture.product-card__media--main"
PRODUCT_CARD_MEDIA_HOVER = "picture.product-card__media--hover"
PRODUCT_CARD_BADGE = ".badge"
PRODUCT_CARD_COVER_LINK = "a.cover"
PRODUCT_CARD_TIME = "time"

# Product Card Rating Selectors
RATING_STARS_ICONS = ".rating-stars__icons"
RATING_STARS_COUNT = ".rating-stars__count"

# Product Detail Page Selectors
PDP_ACCORDION = ".pdp__accordion"
PDP_ACCORDION_CONTENT = ".pdp__accordion-content"
PDP_ACCORDION_CONTENT_PARAGRAPH = ".pdp__accordion-content p"
PDP_LIFESTYLE_GRID = ".pdp__lifestyle-grid figure"

# Navigation Selectors
NAV_SHOP_MENU = 'div[data-nav-menu="shop"]'
MENU_COL = ".menu__col"
NAV_MENU_HEADLINE = "strong.nav__menu-headline"
HOVER_LINK = "a.hover-u"

# Modal Selectors
MODAL_CLOSE_BUTTON = "button.big-close"

# Generic Selectors
IMG_TAG = "img"
VIDEO_TAG = "video"
PICTURE_TAG = "picture"
STRONG_TAG = "strong"
PARAGRAPH_TAG = "p"
SUMMARY_TAG = "summary"

# Container Selectors
PRODUCTS_CONTAINER = "#products"
IMAGE_CARD = ".image-card"

# Dynamic Attribute Selectors (functions to generate selectors)
def get_price_selector(element_name: str, modifier: str) -> str:
    """Generate price selector for specific element and modifier"""
    return f"{element_name}[data-product-card-price-{modifier}]"

def get_media_selector(modifier: str) -> str:
    """Generate media selector for specific modifier (main/hover)"""
    return f"picture.product-card__media--{modifier}"