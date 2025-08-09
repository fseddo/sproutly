from bs4 import Tag


def get_item_review_info(tile: Tag):
    reviews_rating_tag = tile.select_one(".rating-stars__icons")
    reviews_rating = reviews_rating_tag.get("content") or "".strip() if reviews_rating_tag else "0"

    reviews_count_tag = tile.select_one(".rating-stars__count")
    reviews_count = reviews_count_tag.get("content") or "".strip() if reviews_count_tag else "0"
    return reviews_rating, reviews_count
