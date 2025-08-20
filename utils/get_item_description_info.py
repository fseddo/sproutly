from playwright.async_api import Locator


async def get_item_description_info(tile: Locator, id: str):
    # --- Product Description and Care Instructions ---
    paragraphs = await tile.locator("p").all()
    # Concatenate outerHTML of all <p> tags
    paragraph_htmls = []
    print(f"  ↪️ Accordion [{id}] contains {len(paragraphs)} paragraph(s)")
    for i, p in enumerate(paragraphs):
        html = await p.evaluate("(el) => el.outerHTML")
        paragraph_htmls.append(html)
        text = await p.text_content()
        snippet = text.strip()[:60] if text else ""
        print(f"    • Paragraph [{i}]: {snippet}")

    section_html = "".join(paragraph_htmls)

    if not section_html:
        print("  ⚠️ No product information found.")
        return None

    return section_html