import logging
from typing import Optional, Dict, Any
from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def get_item_media_info(page: Page) -> Optional[Dict[str, Any]]:
    """Extract media information (images and videos) from product detail page using Playwright"""
    try:
        # --- Media (Images + Video) ---
        lifestyle_items = page.locator(".pdp__lifestyle-grid figure")
        item_count = await lifestyle_items.count()
        
        if item_count == 0:
            logger.debug("⚠️ No lifestyle media found.")
            return None

        main_detail_src = None
        is_main_detail_video = False
        detail_image_1_src = None
        detail_image_2_src = None

        logger.debug(f"🎞 Found {item_count} lifestyle media item(s)")

        for idx in range(item_count):
            item = lifestyle_items.nth(idx)
            logger.debug(f"• Media [{idx}]:")

            # Try to get <video> src first (videos take priority over images for main detail)
            video_locator = item.locator("video")
            if await video_locator.count() > 0 and not main_detail_src:
                video_src = await video_locator.get_attribute("data-in-view-video-src")
                if video_src and isinstance(video_src, str):
                    video_src = video_src.strip()
                    if video_src.startswith("//"):
                        video_src = "https:" + video_src
                    main_detail_src = video_src
                    is_main_detail_video = True
                    logger.debug(f"  ▶️ Video found: {video_src}")

            # Try to get <img> src from <picture>
            picture_locator = item.locator("picture").first
            if await picture_locator.count() > 0:
                img_locator = picture_locator.locator("img")
                if await img_locator.count() > 0:
                    img_src = await img_locator.get_attribute("src")
                    if img_src and isinstance(img_src, str):
                        img_src = img_src.strip()
                        if img_src.startswith("//"):
                            img_src = "https:" + img_src

                        # Assign based on index and priority
                        if idx == 0 and not main_detail_src:  # Only if no video was found
                            main_detail_src = img_src
                            logger.debug(f"  🖼 Main Detail Image: {img_src}")
                        elif idx == 1:
                            detail_image_1_src = img_src
                            logger.debug(f"  🖼 Detail Image 1: {img_src}")
                        elif idx == 2:
                            detail_image_2_src = img_src
                            logger.debug(f"  🖼 Detail Image 2: {img_src}")

        return {
            "main_detail_src": main_detail_src, 
            "is_main_detail_video": is_main_detail_video, 
            "detail_image_1_src": detail_image_1_src, 
            "detail_image_2_src": detail_image_2_src
        }
        
    except Exception as e:
        logger.warning(f"Failed to extract media info: {e}")
        return None