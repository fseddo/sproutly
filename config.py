"""
Configuration classes for the Urban Stems scraper.
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ScrapingConfig:
    """Configuration for scraping parameters"""
    
    # Target configuration
    base_url: str = "https://urbanstems.com"  
    category_discovery_url: str = "https://urbanstems.com"  # URL to discover categories from
    
    # Page type limits
    max_categories: Optional[int] = None  # Limit number of categories to scrape
    max_collections: Optional[int] = None  # Limit number of collections to scrape  
    max_occasions: Optional[int] = None   # Limit number of occasions to scrape
    
    # Browser configuration
    viewport_width: int = 1280
    viewport_height: int = 800
    headless: bool = False
    
    # Scrolling configuration
    scroll_step_divisor: float = 1.6 # viewport_height // this = scroll_step
    initial_wait: float = 0.2  # seconds to wait after page load
    scroll_wait: float = 0.2  # seconds to wait after each scroll
    
    # Modal handling
    modal_wait_timeout: int = 8000  # milliseconds to wait for modal
    modal_close_wait: float = 0.5  # seconds to wait after closing modal
    
    # Error handling
    max_retries: int = 1
    
    # Output configuration
    output_file: str = "products.json"
    
    # Limits (useful for testing)
    max_products: Optional[int] = None
    max_products_per_category: Optional[int] = None  # Limit per category
    
    @property
    def scroll_step(self) -> int:
        """Calculate scroll step based on viewport height"""
        return int(self.viewport_height // self.scroll_step_divisor)
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.scroll_wait < 0.2:
            raise ValueError("scroll_wait should be at least 0.2 seconds")
        
        if self.max_retries < 1:
            raise ValueError("max_retries should be at least 1")
        
        if self.viewport_width < 800 or self.viewport_height < 600:
            raise ValueError("Viewport should be at least 800x600")

@dataclass 
class ProductConfig:
    """Configuration for product processing"""
        
    # Processing limits
    max_detail_fetch_retries: int = 2
    detail_fetch_timeout: int = 30  # seconds
    
    # Variation detection
    enable_variation_linking: bool = True
    
    # Image processing
    download_images: bool = False
    image_output_dir: str = "images"

# Predefined configurations for common use cases
class ConfigPresets:
    """Predefined configuration presets"""
    
    @staticmethod
    def development() -> ScrapingConfig:
        """Development configuration - fast, visible browser, limited products"""
        return ScrapingConfig(
            headless=False,
            initial_wait=2,
            scroll_wait=1.5,
            max_products=10,
            max_products_per_category=5,  # 5 products per category for dev
            output_file="dev_products.json"
        )
    
    @staticmethod
    def testing() -> ScrapingConfig:
        """Testing configuration - very fast, headless, very limited"""
        return ScrapingConfig(
            headless=True,
            initial_wait=1,
            scroll_wait=1.0,
            max_products=6,
            max_products_per_category=3,  # 3 products per category for testing
            max_retries=2,
            output_file="test_products.json"
        )
    
    @staticmethod
    def production() -> ScrapingConfig:
        """Production configuration - comprehensive, headless, robust"""
        return ScrapingConfig(
            headless=True,
            initial_wait=3,
            scroll_wait=2.0,
            max_retries=5,
            output_file="products.json"
        )
    
    @staticmethod
    def fast() -> ScrapingConfig:
        """Fast configuration - quick scraping with reasonable reliability"""
        return ScrapingConfig(
            headless=True,
            initial_wait=1,
            scroll_wait=1.0,
            max_retries=2,
            max_products_per_category=20,
            output_file="fast_products.json"
        )