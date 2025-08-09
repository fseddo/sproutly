from pathlib import Path
import time
import json
from playwright.sync_api import sync_playwright
from utils import add_products, hydrate_type_from_folder


start_time = time.time()

with sync_playwright() as p:

    products = []
    variation_lookup = {}
    
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    category_folder = Path("data/category")
    for file_path in category_folder.glob("*.html"):
        category_name = file_path.stem 
        add_products(str(file_path), products, variation_lookup, context, category_name)

    hydrate_type_from_folder("data/collection", products, "collection")
    hydrate_type_from_folder("data/occasion", products, "occasion")

    browser.close()


# Save to JSON file
with open("products.json", "w") as f:
    json.dump(products, f, indent=2)

end_time = time.time()
duration = end_time - start_time

print(f"✅ Scraped {len(products)} products and saved to 'products.json'")
print(f"\n⏱️ Script finished in {duration:.2f} seconds.")
