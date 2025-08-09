from bs4 import Tag


def get_image_src(tile: Tag, modifier: str):
    picture_tag = tile.select_one("picture.product-card__media--" + modifier)
    image_tag = picture_tag.select_one("img") if picture_tag else None

    image_src = ""
    if image_tag:
        raw_src = image_tag.get("src") or image_tag.get("data-src") or ""
        if isinstance(raw_src, list):
            raw_src = raw_src[0]  # take the first item if it's a list
        if isinstance(raw_src, str):
            image_src = raw_src.strip()
            if image_src.startswith("//"):
                image_src = "https:" + image_src
    
    return image_src
