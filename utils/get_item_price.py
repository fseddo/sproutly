from bs4 import Tag


def get_item_price(tile: Tag, element_name: str, modifier: str): 
    price_tag = tile.select_one(element_name + "[data-product-card-price-" + modifier + "]")
    price_text = price_tag.get_text(strip=True).replace("$", "") if price_tag else None
    price = int(float(price_text) * 100) if price_text else None
    return price
