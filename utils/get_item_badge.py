from bs4 import Tag


def get_item_badge(tile: Tag):
    badge_tag = tile.select_one(".badge__text")
    badge_text = badge_tag.get_text(strip=True) if badge_tag else None
    return badge_text
