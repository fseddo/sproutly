from playwright.async_api import Locator


async def get_item_url(tile: Locator, base_url: str):
    relative_url = await tile.locator("a.cover").first.get_attribute("href")
    full_url = base_url + relative_url if isinstance(relative_url, str) else None
    return full_url
