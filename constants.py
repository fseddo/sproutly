"""
Constants for Urban Stems Scraper

This module contains all the magic numbers, configuration values, and constants
used throughout the scraper to improve maintainability and avoid duplication.
"""

from typing import Set

# URLs and Base Configuration
BASE_URL = "https://urbanstems.com"
CATEGORY_DISCOVERY_URL = f"{BASE_URL}/"

# Collections to ignore during discovery
IGNORED_COLLECTIONS: Set[str] = {'shop all', 'today', 'tomorrow'}

# Timing Constants (in seconds unless specified)
SCROLL_CHECK_INTERVAL = 0.05  # Reduced from 0.2s for better performance
SCROLL_MAX_WAIT_TIME = 3.0
MODAL_WAIT_TIMEOUT = 8.0
DEFAULT_INITIAL_WAIT = 0.2
DEFAULT_SCROLL_WAIT = 0.2

# Timeouts (in milliseconds)
PAGE_CONTENT_TIMEOUT = 5000
SELECTOR_WAIT_TIMEOUT = 5000
DETAIL_PAGE_TIMEOUT = 10000

# UI and Layout Constants
VIEWPORT_TOLERANCE = 50
DEFAULT_VIEWPORT_WIDTH = 1280
DEFAULT_VIEWPORT_HEIGHT = 800

# Product Processing Constants
DEFAULT_STOCK = 100
PRICE_MULTIPLIER = 100  # Convert dollars to cents
MAX_RETRIES_DEFAULT = 1
MAX_SCROLL_ATTEMPTS_DEFAULT = 3

# Scroll Configuration
SCROLL_STEP_DIVISOR = 1.6
SCROLL_BEHAVIOR = "smooth"
SCROLL_POSITION_TOP = 0

# Logging and Debug
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# File Processing
DEFAULT_OUTPUT_FILE = "products.json"

# Rate Limiting
DEFAULT_CONCURRENT_LIMIT = 3