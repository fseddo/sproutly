import asyncio
from typing import Callable, List, Dict, Any, Optional

async def scroll_and_extract(
    page,
    extractors: List[Dict[str, Any]],
    scroll_step: int = 80,
    scroll_pause: float = 2.0,
    max_scroll: Optional[int] = None
) -> Dict[str, List[Any]]:

    # Prepare results dict and seen sets for deduplication
    results = {ex['name']: [] for ex in extractors}
    seen_ids = {ex['name']: set() for ex in extractors}

    scroll_height = await page.evaluate("document.body.scrollHeight")
    pos = 0

    while pos < scroll_height and (max_scroll is None or pos < max_scroll):
        await page.evaluate(f"window.scrollTo(0, {pos})")
        await asyncio.sleep(scroll_pause)

        for ex in extractors:
            locator = page.locator(ex['locator_selector'])
            count = await locator.count()

            for i in range(count):
                card = locator.nth(i)
                try:
                    if not await card.is_visible():
                        continue
                    await card.scroll_into_view_if_needed()

                    data = await ex['extract_func'](card)
                    if data is None:
                        continue

                    data_id = data.get("id")
                    if data_id and data_id in seen_ids[ex['name']]:
                        continue
                    if data_id:
                        seen_ids[ex['name']].add(data_id)

                    results[ex['name']].append(data)

                except Exception as e:
                    print(f"Error processing {ex['name']} element {i}: {e}")

        new_scroll_height = await page.evaluate("document.body.scrollHeight")
        if new_scroll_height == scroll_height:
            break
        scroll_height = new_scroll_height
        pos += scroll_step

    return results
