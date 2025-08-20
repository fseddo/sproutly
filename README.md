# Sproutly

**Sproutly** is a modern web scraper built with Playwright that gathers structured product data from UrbanStems to seed a future e-commerce prototype project.

## Features

- **Dynamic Scraping**: Uses Playwright browser automation to handle JavaScript-rendered content
- **Intelligent Discovery**: Automatically discovers categories, collections, and occasions from site navigation
- **Comprehensive Product Data**: Extracts names, prices, images, descriptions, delivery info, and variant relationships
- **Cross-Page Product Tracking**: Handles products that appear in multiple categories/collections
- **Configurable Limits**: Flexible controls for testing and production scraping
- **Robust Error Handling**: Retry logic and graceful failure handling
- **Clean JSON Output**: Structured data ready for database seeding

## Architecture

- **Browser Automation**: Playwright handles dynamic content and user interactions
- **Modular Design**: Separate modules for scraping, product processing, and detail extraction
- **Configuration System**: Preset configurations for different use cases
- **Command Line Interface**: Easy-to-use CLI with extensive options

## Tech Stack

- **Python 3.8+**
- **Playwright** - Browser automation and dynamic content handling
- **AsyncIO** - Asynchronous processing for performance

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

### Basic Usage
```bash
python main.py
```

### Common Examples
```bash
# Fast mode with limits
python main.py --fast --max-products 20

# Test specific page types
python main.py --max-categories 0 --max-collections 4 --max-occasions 0

# Development mode with custom settings
python main.py --headless --max-products 50 --initial-wait 0.5
```

### Configuration Options

- `--fast`: Quick mode with reduced waits
- `--headless`: Run browser without GUI
- `--max-products <N>`: Limit total products scraped
- `--max-categories <N>`: Limit number of categories (0 to skip)
- `--max-collections <N>`: Limit number of collections (0 to skip)
- `--max-occasions <N>`: Limit number of occasions (0 to skip)
- `--output FILE`: Custom output file path

## Output

The scraper generates a JSON file with structured product data including:

- Product details (name, price, description)
- Images and media information
- Category, collection, and occasion associations
- Variant relationships and cross-references
- Delivery and availability information


## Ethical Use and Disclaimer

- This scraper is intended solely for personal, educational, and prototyping purposes.
- The project respects the website’s terms of service and is not intended for commercial use or redistribution of protected content.