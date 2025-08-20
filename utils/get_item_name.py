from playwright.async_api import Locator


async def get_item_name(tile: Locator):
    name_locator = tile.locator("a.product-card__title")
    return ((await name_locator.first.inner_text()).strip().replace("View ", "", 1)) if await name_locator.count() > 0 else "Unnamed Product"        
