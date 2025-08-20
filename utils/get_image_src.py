from playwright.async_api import Locator


async def get_image_src(tile: Locator, modifier: str) -> str:
    picture_tag = tile.locator(f"picture.product-card__media--{modifier}").first
    image_tag = picture_tag.locator("img").first

    if await image_tag.count() == 0:
        return ""

    raw_src = await image_tag.get_attribute("src") or await image_tag.get_attribute("data-src") or ""
    
    if isinstance(raw_src, list) and raw_src:
        raw_src = raw_src[0]

    if isinstance(raw_src, str):
        image_src = raw_src.strip()
        if image_src.startswith("//"):
            image_src = "https:" + image_src
        return image_src

    return ""
