from bs4 import BeautifulSoup

from utils import get_item_name


def hydrate_item_types(file_location: str, products: list, field: str, value: str):
    with open(file_location, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    print(f"✅ Page loaded. Parsing {value} {field}(s)...")

    product_tiles = soup.select(".product-card")
    if not product_tiles:
        print(f"⚠️ No {value} {field}s found. You might be blocked from making additional requests.")
        return

    for tile in product_tiles:
        name = get_item_name(tile)
        if not name:
            continue

        for product in products:
            if product["name"] == name:
                print(f"    ✅ Updated {name}'s {field} to: {value}")
                if isinstance(product.get(field), list):
                    product[field].append(value)
                elif product.get(field):
                    product[field] = [product[field], value]
                else:
                    product[field] = [value]