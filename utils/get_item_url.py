from bs4 import Tag


def get_item_url(tile: Tag, base_url: str):
    link_tag = tile.select_one("a.cover")
    relative_url = link_tag.get("href", "") if link_tag else ""
    full_url = base_url + relative_url if isinstance(relative_url, str) else None
    return full_url
