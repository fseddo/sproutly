from playwright.async_api import Locator



async def get_item_price(tile: Locator, element_name: str, modifier: str): 
    price = None
    price_locator = tile.locator(f"{element_name}[data-product-card-price-{modifier}]")
    if await price_locator.count() > 0:
        raw_text = (await price_locator.inner_text()).strip().replace("$", "")
        if raw_text:
            try:
                price = int(float(raw_text) * 100)
            except ValueError:
                price = None
        else:
            price = None

    return price

