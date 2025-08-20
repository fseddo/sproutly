from playwright.async_api import Locator


async def get_item_review_info(tile: Locator):
    review_rating = "0"
    review_count = "0"

    reviews_rating_locator = tile.locator(".rating-stars__icons")
    if await reviews_rating_locator.count() > 0:
        review_rating = await reviews_rating_locator.get_attribute("content") or "0"

    reviews_count_locator = tile.locator(".rating-stars__count")
    if await reviews_count_locator.count() > 0:
        review_count = await reviews_count_locator.get_attribute("content") or "0"

    return review_rating.strip(), review_count.strip()
