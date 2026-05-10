"""
Addon extractor for Urban Stems product detail pages.

Given a Page already navigated to a PDP (with any blocking modal dismissed),
extracts addon-type metadata (e.g., Vase, Gifts) and the individual addon
items inside each type's menu.

The third addon type on the site has a different DOM structure and is out of
scope; processing is limited to the first N types (default 2).
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from playwright.async_api import Page, Locator

from scraper import normalize_img_src

logger = logging.getLogger(__name__)

DEFAULT_MAX_ADDON_TYPES = 2

# Maps an addon-type label (case-insensitive substring) to a short slug.
# Falls back to index-based mapping (see _slug_for_addon_type) for unknowns.
ADDON_TYPE_KEYWORDS = {
    "vase": "vase",
    "gift": "gift",
    "extra": "gift",  # "Add Something Extra"
}
ADDON_TYPE_FALLBACK_BY_INDEX = ["vase", "gift"]

# Pattern used to recognize the lazy-load placeholder src.
LOADING_PLACEHOLDER_RE = re.compile(r"loading\.svg", re.IGNORECASE)

# Addon-type list (PDP)
ADDON_ITEMS = ".pdp__addon-items"
ADDON_ITEM = ".pdp__addon-item"
ADDON_ITEM_LABEL = ".pdp__addon-item-label"
ADDON_ITEM_INFO = ".pdp__addon-item-info"
ADDON_ITEM_MEDIA_IMG = ".pdp__addon-item-media img"

# Addon-type menu (opens when an addon-item is clicked).
# Like the detail views, addon menus are pre-rendered per type, so we
# always target the currently-visible one.
ADDON_MENU = ".pdp__addon-menu"
ADDON_MENU_VISIBLE = ".pdp__addon-menu:visible"
ADDON_CARD = ".pdp__addon-card"
ADDON_LEARN_MORE = "summary.pdp__addon-learn-more"

# Single-addon detail view (opens when a card's learn-more is clicked).
# The container has id="learn-more--{someId}" and class "menu menu--right".
# Detail containers are pre-rendered per card, so we always filter to the
# currently-visible one.
DETAIL_CONTAINER = '[id^="learn-more--"]'
DETAIL_VISIBLE = '[id^="learn-more--"]:visible'
DETAIL_HEADLINE = ".pdp__addon-menu-content .headline"
DETAIL_SUBLINE = ".pdp__addon-menu-content .subline"
DETAIL_DESCRIPTION = ".pdp__addon-menu-content .learn-more__description"
DETAIL_IMAGE = "figure.learn-more__image img"
DETAIL_BUTTON = ".learn-more__btn"

TRANSITION_WAIT = 0.4
SELECTOR_TIMEOUT = 8000

PRICE_RE = re.compile(r"\$(\d+(?:\.\d+)?)")


async def _safe_inner_text(locator: Locator) -> Optional[str]:
    if await locator.count() == 0:
        return None
    text = await locator.first.inner_text()
    return text.strip() if text else None


def _slug_for_addon_type(label: Optional[str], index: int) -> str:
    """Resolve an addon-type label to a short slug like 'vase' or 'gift'."""
    if label:
        lower = label.lower()
        for keyword, slug in ADDON_TYPE_KEYWORDS.items():
            if keyword in lower:
                return slug
    if index < len(ADDON_TYPE_FALLBACK_BY_INDEX):
        return ADDON_TYPE_FALLBACK_BY_INDEX[index]
    return f"type_{index}"


async def _extract_real_img_src(img_loc: Locator) -> Optional[str]:
    """
    Extract an image src, working around lazy-load placeholders.

    Many lazy-loaded images keep `loading.svg` in `src` until the image
    scrolls into the user's viewport, with the real URL in `data-src` or
    `srcset`. We try those alternatives before falling back to `src`.
    """
    if await img_loc.count() == 0:
        return None
    img = img_loc.first

    candidates: List[Optional[str]] = []
    candidates.append(await img.get_attribute("data-src"))
    candidates.append(await img.get_attribute("src"))

    srcset = await img.get_attribute("srcset") or await img.get_attribute("data-srcset")
    if srcset:
        # srcset format: "url1 1x, url2 2x" or "url1 100w, url2 200w".
        # First entry is usually the smallest/default real URL.
        first_entry = srcset.split(",")[0].strip()
        if first_entry:
            candidates.append(first_entry.split()[0])

    for url in candidates:
        if url and not LOADING_PLACEHOLDER_RE.search(url):
            return normalize_img_src(url)

    return None


async def _extract_addon_type_meta(item: Locator, index: int) -> Dict[str, Optional[str]]:
    label = await _safe_inner_text(item.locator(ADDON_ITEM_LABEL))
    info = await _safe_inner_text(item.locator(ADDON_ITEM_INFO))
    image = await _extract_real_img_src(item.locator(ADDON_ITEM_MEDIA_IMG))

    return {
        "addon_type": _slug_for_addon_type(label, index),
        "label": label,
        "info": info,
        "image": image,
    }


def _parse_price_to_cents(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    match = PRICE_RE.search(text)
    if not match:
        return None
    try:
        return int(round(float(match.group(1)) * 100))
    except ValueError:
        return None


async def _extract_addon_detail(page: Page, addon_type: str) -> Dict[str, Any]:
    detail = page.locator(DETAIL_VISIBLE).first

    name = await _safe_inner_text(detail.locator(DETAIL_HEADLINE))
    subtitle = await _safe_inner_text(detail.locator(DETAIL_SUBLINE))
    description = await _safe_inner_text(detail.locator(DETAIL_DESCRIPTION))
    img_src = await _extract_real_img_src(detail.locator(DETAIL_IMAGE))

    button_text = await _safe_inner_text(detail.locator(DETAIL_BUTTON))
    price = _parse_price_to_cents(button_text)

    return {
        "name": name,
        "subtitle": subtitle,
        "description": description,
        "img_src": img_src,
        "price": price,
        "addon_type": addon_type,
    }


async def _close_detail_view(page: Page) -> None:
    detail = page.locator(DETAIL_VISIBLE).first
    if await detail.count() == 0:
        logger.debug("No visible detail view to close")
        return
    close_btn = detail.locator(":scope > .menu__header .menu__close").first
    try:
        if await close_btn.count() > 0:
            await close_btn.click(timeout=3000)
        else:
            logger.warning("Detail close button not found via direct-child scope")
    except Exception as e:
        logger.warning(f"Detail close click failed: {e}")

    try:
        await page.wait_for_selector(DETAIL_VISIBLE, state="hidden", timeout=3000)
        return
    except Exception:
        logger.warning("Detail view still visible after close click; trying Escape")

    try:
        await page.keyboard.press("Escape")
        await page.wait_for_selector(DETAIL_VISIBLE, state="hidden", timeout=3000)
    except Exception as e:
        logger.error(f"Failed to close detail view via Escape: {e}")
        await asyncio.sleep(TRANSITION_WAIT)


async def _close_addon_menu(page: Page) -> None:
    logger.debug("Closing addon-type menu")
    menu = page.locator(ADDON_MENU_VISIBLE).first
    if await menu.count() == 0:
        logger.debug("No visible addon menu to close")
        return

    # Direct-child scope: the addon-menu's own header is a direct child,
    # so this excludes any nested detail-view close buttons.
    close_btn = menu.locator(":scope > .menu__header .menu__close").first
    try:
        if await close_btn.count() > 0:
            await close_btn.click(timeout=3000)
        else:
            logger.warning("Addon-menu close button not found via direct-child scope")
    except Exception as e:
        logger.warning(f"Addon-menu close click failed: {e}")

    try:
        await menu.wait_for(state="hidden", timeout=3000)
        logger.debug("Addon menu closed")
        return
    except Exception:
        logger.warning("Addon menu still visible after close click; trying Escape")

    try:
        await page.keyboard.press("Escape")
        await menu.wait_for(state="hidden", timeout=3000)
        logger.debug("Addon menu closed via Escape")
    except Exception as e:
        logger.error(f"Failed to close addon menu via Escape: {e}")
        await asyncio.sleep(TRANSITION_WAIT)


async def _process_addon_type(page: Page, item: Locator, addon_type: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    await item.scroll_into_view_if_needed()
    await item.click()

    try:
        await page.wait_for_selector(
            f"{ADDON_MENU_VISIBLE} {ADDON_CARD}", state="visible", timeout=SELECTOR_TIMEOUT
        )
    except Exception as e:
        logger.error(f"Addon menu did not open for type '{addon_type}': {e}")
        return results

    await asyncio.sleep(TRANSITION_WAIT)

    menu = page.locator(ADDON_MENU_VISIBLE).first
    card_count = await menu.locator(ADDON_CARD).count()
    logger.info(f"  Found {card_count} addon card(s) under '{addon_type}'")

    for i in range(card_count):
        logger.info(f"  → Card [{i}/{card_count - 1}] in '{addon_type}': start")
        try:
            card = menu.locator(ADDON_CARD).nth(i)
            logger.debug(f"    locating card; scrolling into view")
            # Container-aware scroll: scrollIntoView climbs ancestors and
            # adjusts whichever scroll container holds the card.
            await card.evaluate(
                "el => el.scrollIntoView({block: 'nearest', behavior: 'instant'})"
            )
            await asyncio.sleep(0.1)

            learn_more = card.locator(ADDON_LEARN_MORE)
            lm_count = await learn_more.count()
            logger.debug(f"    learn-more count: {lm_count}")
            if lm_count == 0:
                logger.warning(
                    f"  Card [{i}] in '{addon_type}' has no learn-more summary; skipping"
                )
                continue

            logger.debug(f"    clicking learn-more")
            await learn_more.first.click(timeout=5000)

            try:
                await page.wait_for_selector(
                    f"{DETAIL_VISIBLE} {DETAIL_IMAGE}",
                    state="visible",
                    timeout=SELECTOR_TIMEOUT,
                )
            except Exception as e:
                logger.error(
                    f"  Detail view did not open for card [{i}] in '{addon_type}': {e}"
                )
                continue

            await asyncio.sleep(TRANSITION_WAIT)

            detail = await _extract_addon_detail(page, addon_type)
            results.append(detail)
            price_str = f"${(detail['price'] or 0) / 100:.2f}" if detail.get("price") else "?"
            logger.info(f"    ✅ {detail.get('name')} ({price_str})")

            await _close_detail_view(page)

        except Exception as e:
            logger.error(
                f"  Failed to process card [{i}] in '{addon_type}': {e}", exc_info=True
            )
            # Try to recover so we can continue with the next card.
            try:
                await _close_detail_view(page)
            except Exception:
                pass

    logger.info(f"  All cards processed for '{addon_type}'; closing menu")
    await _close_addon_menu(page)
    return results


async def extract_addons(
    page: Page, max_addon_types: int = DEFAULT_MAX_ADDON_TYPES
) -> Dict[str, List[Any]]:
    """
    Extract addon types and addon items from a PDP.

    Assumes `page` is already navigated to the PDP and any blocking modal
    has been dismissed. Returns {"addon_types": [...], "addons": [...]}.
    """
    addon_types: List[Dict[str, Any]] = []
    addons: List[Dict[str, Any]] = []

    try:
        await page.wait_for_selector(ADDON_ITEMS, timeout=SELECTOR_TIMEOUT)
    except Exception as e:
        logger.error(f"Addon items section not found: {e}")
        return {"addon_types": addon_types, "addons": addons}

    items_container = page.locator(ADDON_ITEMS).first
    items = items_container.locator(f":scope > {ADDON_ITEM}")
    total = await items.count()
    type_count = min(total, max_addon_types)
    logger.info(f"Found {total} addon type item(s); processing first {type_count}")

    for i in range(type_count):
        item = items.nth(i)
        try:
            meta = await _extract_addon_type_meta(item, i)
            logger.info(f"📦 Addon type [{i}]: {meta.get('label')} → {meta.get('addon_type')}")
            addon_types.append(meta)

            type_addons = await _process_addon_type(page, item, meta["addon_type"])
            addons.extend(type_addons)

        except Exception as e:
            logger.error(f"Failed to process addon type [{i}]: {e}", exc_info=True)

    return {"addon_types": addon_types, "addons": addons}
