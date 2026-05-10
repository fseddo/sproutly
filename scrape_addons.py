"""
Standalone scraper for Urban Stems product addons.

Visits a single PDP (default: /products/the-peace), opens each addon-type
menu, opens each addon's detail view, and extracts addon metadata to
addons.json.

Usage:
    python scrape_addons.py
    python scrape_addons.py --headless
    python scrape_addons.py --product-slug=the-peace
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from playwright.async_api import async_playwright, Page

from addon_extractor import extract_addons
from constants import BASE_URL, MODAL_WAIT_TIMEOUT

logger = logging.getLogger(__name__)

DEFAULT_PRODUCT_SLUG = "the-peace"
DEFAULT_OUTPUT = "addons.json"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


async def dismiss_modal(page: Page) -> None:
    """Close the welcome/promo modal if it appears on first load."""
    close_button = "button[aria-label='Close dialog']"
    try:
        await page.wait_for_selector(close_button, timeout=int(MODAL_WAIT_TIMEOUT * 1000))
        await page.click(close_button, force=True)
        logger.info("✅ Closed modal popup")
        await asyncio.sleep(0.5)
    except Exception:
        logger.debug("No modal popup detected")


async def run(slug: str, headless: bool, output: str) -> None:
    url = f"{BASE_URL}/products/{slug}"
    logger.info(f"🚀 Visiting {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(1)
            await dismiss_modal(page)

            result = await extract_addons(page)

            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            logger.info(
                f"✅ Saved {len(result['addon_types'])} addon type(s) "
                f"and {len(result['addons'])} addon(s) to {output_path}"
            )
        finally:
            await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape Urban Stems addons from a single PDP"
    )
    parser.add_argument(
        "--product-slug",
        default=DEFAULT_PRODUCT_SLUG,
        help=f"Product slug under /products/ (default: {DEFAULT_PRODUCT_SLUG})",
    )
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument(
        "--output", "-o", default=DEFAULT_OUTPUT, help="Output JSON path"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    setup_logging(args.log_level)
    asyncio.run(run(args.product_slug, args.headless, args.output))


if __name__ == "__main__":
    main()
