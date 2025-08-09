import os
from utils import hydrate_item_types


def hydrate_type_from_folder(folder_path: str, products: list, field: str):
    for filename in os.listdir(folder_path):
        if filename.endswith(".html"):
            value = os.path.splitext(filename)[0]  # strip ".html"
            file_path = os.path.join(folder_path, filename)
            hydrate_item_types(file_path, products, field, value)