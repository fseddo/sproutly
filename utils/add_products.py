from bs4 import BeautifulSoup
from playwright.sync_api import BrowserContext
from utils import add_product


def add_products(file_location: str, products: list, variation_lookup: dict, context: BrowserContext, item_category: str): 
    with open(file_location, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    print(f"✅ Page loaded. Parsing {item_category}s...")


    # This selector targets product tiles on the UrbanStems collection
    product_tiles = soup.select(".product-card")

    if not product_tiles:
        print(f"⚠️ No {item_category}s found. You might be blocked from making additional requests.")
        exit()

    for idx, tile in enumerate(product_tiles, start=1):
        #This selector confirms the product tile has a reference to an individual details page
        link_tag = tile.select_one("a.cover")
        if not link_tag:
            continue
        
        add_product(tile, idx, products, variation_lookup, context, item_category)
    
