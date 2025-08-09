from bs4 import BeautifulSoup, Tag


def get_item_media_info(soup: BeautifulSoup):
     # --- Media (Images + Video) ---
    lifestyle_items = soup.select(".pdp__lifestyle-grid figure")
    if not lifestyle_items:
        print("  ⚠️ No lifestyle media found.")
        return None

    main_detail_src = None
    is_main_detail_video = False
    detail_image_1_src = None
    detail_image_2_src = None

    print(f"  🎞 Found {len(lifestyle_items)} lifestyle media item(s)")

    for idx, item in enumerate(lifestyle_items):
        print(f"    • Media [{idx}]:")

        # Try to get <video> src
        video_tag = item.select_one("video")
        if video_tag and not main_detail_src:
            main_detail_src = video_tag.get("data-in-view-video-src")
            if isinstance(main_detail_src, str):
                main_detail_src = main_detail_src.strip()
                if main_detail_src.startswith("//"):
                    main_detail_src = "https:" + main_detail_src
                    is_main_detail_video = True
                print(f"      ▶️ Video found: {main_detail_src}")

        # Try to get <img> src from <picture>
        first_tag = next((child for child in item.children if isinstance(child, Tag)), None)
        if first_tag and first_tag.name == "picture":
            img_tag = first_tag.select_one("img")
            img_src = img_tag.get("src") if img_tag else None
            if isinstance(img_src, str):
                img_src = img_src.strip()
                if img_src.startswith("//"):
                    img_src = "https:" + img_src

                if idx == 0:
                    main_detail_src = img_src
                    print(f"      🖼 Main Detail Image: {img_src}")
                if idx == 1:
                    detail_image_1_src = img_src
                    print(f"      🖼 Detail Image 1: {img_src}")
                elif idx == 2:
                    detail_image_2_src = img_src
                    print(f"      🖼 Detail Image 2: {img_src}")
    return {
        "main_detail_src":main_detail_src, 
        "is_main_detail_video":is_main_detail_video, 
        "detail_image_1_src":detail_image_1_src, 
        "detail_image_2_src":detail_image_2_src
        }