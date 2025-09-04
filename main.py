from typing import List, Dict
"""
Urban Stems Scraper - Main Execution Script

This script runs the Urban Stems flower scraper with configurable options.
Run with: python main.py [options]
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict

from config import ScrapingConfig
from scraper import UrbanStemsScraper

def setup_logging(level: str = "INFO", log_file: bool = False) -> None:
    """Setup logging configuration"""
    log_level = getattr(logging, level.upper())
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Scrape Urban Stems flower products",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Basic options
    parser.add_argument(
        "--headless", 
        action="store_true",
        help="Run browser in headless mode"
    )
    
    
    parser.add_argument(
        "--output", "-o",
        default="products.json",
        help="Output JSON file path"
    )
    
    parser.add_argument(
        "--max-products",
        type=int,
        help="Maximum number of products to scrape (for testing)"
    )
    
    # Timing options
    parser.add_argument(
        "--initial-wait",
        type=float,
        default=0.2,
        help="Seconds to wait after page load"
    )
    
    parser.add_argument(
        "--scroll-wait",
        type=float,
        default=0.2,
        help="Seconds to wait after each scroll"
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        default=1,
        help="Maximum retries per product card"
    )
    
    # Advanced options
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1280,
        help="Browser viewport width"
    )
    
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=800,
        help="Browser viewport height"
    )
    
    parser.add_argument(
        "--base-url",
        default="https://urbanstems.com",
        help="Base URL for the site"
    )
    
    parser.add_argument(
        "--max-per-category",
        type=int,
        help="Maximum products per category"
    )
    
    # Page type limits
    parser.add_argument(
        "--max-categories",
        type=int,
        help="Maximum categories to scrape (0 to skip all categories)"
    )
    
    parser.add_argument(
        "--max-collections", 
        type=int,
        help="Maximum collections to scrape (0 to skip all collections)"
    )
    
    parser.add_argument(
        "--max-occasions",
        type=int, 
        help="Maximum occasions to scrape (0 to skip all occasions)"
    )
    
    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    # Quick presets
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: shorter waits, headless (good for testing)"
    )
    
    return parser.parse_args()

def create_config_from_args(args: argparse.Namespace) -> ScrapingConfig:
    """Create scraping configuration from command line arguments"""

    if args.fast:
        args.initial_wait = 1
        args.scroll_wait = 1.0
        args.headless = True
        print("⚡ Fast mode activated: reduced waits, headless browser")
    
    # Create configuration
    config = ScrapingConfig(
        base_url=args.base_url,
        viewport_width=args.viewport_width,
        viewport_height=args.viewport_height,
        initial_wait=args.initial_wait,
        scroll_wait=args.scroll_wait,
        max_retries=args.max_retries,
        output_file=args.output,
        headless=args.headless,
        max_products=args.max_products,
        max_products_per_category=args.max_per_category,
        max_categories=args.max_categories,
        max_collections=args.max_collections,
        max_occasions=args.max_occasions
    )
    
    return config

def print_config_summary(config: ScrapingConfig) -> None:
    """Print a summary of the configuration"""
    print("\n" + "="*50)
    print("🌸 URBAN STEMS SCRAPER")
    print("="*50)
    print(f"Base URL: {config.base_url}")
    print(f"Output: {config.output_file}")
    print(f"Viewport: {config.viewport_width}x{config.viewport_height}")
    print(f"Headless: {config.headless}")
    print(f"Initial wait: {config.initial_wait}s")
    print(f"Scroll wait: {config.scroll_wait}s")
    print(f"Max retries: {config.max_retries}")
    
    # Category information
    print(f"Category discovery: ✅ Auto-discover from navigation")

    
    # Limits
    if config.max_products:
        print(f"Max products (total): {config.max_products}")
    if config.max_products_per_category:
        print(f"Max products per category: {config.max_products_per_category}")
    if config.max_categories is not None:
        print(f"Max categories: {config.max_categories}")
    if config.max_collections is not None:
        print(f"Max collections: {config.max_collections}")
    if config.max_occasions is not None:
        print(f"Max occasions: {config.max_occasions}")
    
    print("="*50 + "\n")

async def run_scraper(config: ScrapingConfig) -> List[Dict]:
    """Run the scraper with error handling"""
    scraper = UrbanStemsScraper(config)
    
    try:
        print("🚀 Starting scraper...")
        products = await scraper.scrape()
        return products
        
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        logging.error(f"Scraping failed with error: {e}", exc_info=True)
        sys.exit(1)

def main() -> None:
    """Main entry point"""
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Create configuration
    config = create_config_from_args(args)
    
    # Print summary
    print_config_summary(config)
    
    # Ensure output directory exists
    output_path = Path(config.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Run the scraper and get results
    try:
        products = asyncio.run(run_scraper(config))
        print(f"\n🎉 Final result: {len(products)} products successfully scraped!")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()