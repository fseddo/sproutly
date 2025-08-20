from playwright.async_api import Locator

async def get_item_badge(tile: Locator):
    badge_text = None
    if await tile.locator(".badge").count() > 0:
        badge_text = (await tile.locator(".badge").inner_text()).strip()
    return badge_text
