import time
from typing import Optional
from bs4 import BeautifulSoup
from playwright.sync_api import BrowserContext

from utils import get_item_description_info, get_item_media_info

def get_item_detail_info(context: BrowserContext, product_url: Optional[str], index: Optional[int] = None) -> Optional[dict]:
    if not product_url:
        print(f"⚠️ Invalid product link for item [{index}]")
        return None

    page = context.new_page()
    try:
        start_time = time.time()
        page.goto(product_url)
        page.wait_for_selector(".pdp__accordion-content p", timeout=6000)
        soup = BeautifulSoup(page.content(), "html.parser")

        print(f"📦 Fetching details for item [{index}] → {product_url}" if index is not None else f"📦 Fetching details for: {product_url}")

        description_info = get_item_description_info(soup)
        media_info = get_item_media_info(soup)
       
        end_time = time.time()
        duration = start_time - end_time
        print(f"✅ Finished item [{index}] in {duration:.2f} seconds \n{'-' * 60}")

        return {
            "description": description_info["description"] if description_info else None,
            "care_instructions": description_info["care_instructions"] if description_info else None,
            "is_main_detail_video": media_info["is_main_detail_video"] if media_info else None,
            "main_detail_src": media_info["main_detail_src"] if media_info else None,
            "detail_image_1_src": media_info["detail_image_1_src"] if media_info else None,
            "detail_image_2_src": media_info["detail_image_2_src"] if media_info else None,
        }

    except Exception as e:
        print(f"❌ Error scraping item [{index}]: {e}")
        return None
    finally:
        page.close()
