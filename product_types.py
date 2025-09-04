"""
Type definitions for Urban Stems scraper
"""

from typing import TypedDict, Optional, List
from typing_extensions import NotRequired
from enum import Enum


class VariantType(Enum):
    """Product variant types"""
    SINGLE = "single"
    DOUBLE = "double" 
    TRIPLE = "triple"


class AttributeType(Enum):
    """Product attribute types"""
    CATEGORY = "category"
    COLLECTION = "collection"
    OCCASION = "occasion"


class ProductDict(TypedDict):
    """Type definition for a scraped product"""
    id: str
    name: str
    variant_type: Optional[VariantType]
    base_name: str
    url: str
    price: Optional[int]  # Price in cents
    discounted_price: Optional[int]  # Price in cents
    main_image: Optional[str]
    hover_image: Optional[str]
    badge_text: Optional[str]
    delivery_lead_time: Optional[int]
    stock: int
    reviews_rating: Optional[float]
    reviews_count: Optional[int]
    description: Optional[str]
    care_instructions: Optional[str]
    main_detail_src: Optional[str]
    is_main_detail_video: bool
    detail_image_1_src: Optional[str]
    detail_image_2_src: Optional[str]
    collections: List[str]
    occasions: List[str]
    categories: List[str]
    # Variation cross-references (optional)
    single_variation: NotRequired[Optional[str]]
    double_variation: NotRequired[Optional[str]]
    triple_variation: NotRequired[Optional[str]]


class AttributeInfo(TypedDict):
    """Type definition for discovered category/collection/occasion info"""
    name: str  # Display name like "flowers", "friendship", "birthday"
    url: str   # Full URL like "https://urbanstems.com/collections/flowers"
    type: AttributeType  # What kind of attribute this is


# Type aliases for common collections
ProductList = List[ProductDict]
AttributeList = List[AttributeInfo]
VariationMapping = dict[str, dict[VariantType, ProductDict]]  # base_name -> {variant_type -> ProductDict}