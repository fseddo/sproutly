from bs4 import Tag


def get_item_name(tile: Tag):
    name_tag = tile.select_one("a.product-card__title")
    name = str(name_tag.get("title") or "").strip().replace("View ", "", 1) if name_tag else "Unnamed Product"
    return name