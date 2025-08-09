from bs4 import BeautifulSoup


def get_item_description_info(soup: BeautifulSoup):
    # --- Product Description and Care Instructions ---
    accordions = soup.select(".pdp__accordion-content")
    description = None
    care_instructions = None

    for idx, section in enumerate(accordions):
        paragraphs = section.find_all("p")
        section_html = "".join(str(p) for p in paragraphs)

        print(f"  ↪️ Accordion [{idx}] contains {len(paragraphs)} paragraph(s)")
        for i, p in enumerate(paragraphs):
            print(f"    • Paragraph [{i}]: {p.get_text(strip=True)[:60]}")

        if idx == 0:
            description = section_html
        elif idx == 1:
            care_instructions = section_html

    if not description and not care_instructions:
        print("  ⚠️ No product description or care instructions found.")
        return None
    
    return {"care_instructions": care_instructions, "description": description}