from datetime import date, datetime
from typing import Optional
from playwright.async_api import Locator

async def get_item_delivery_lead_time(tile: Locator) -> Optional[int]:
    date_field = await tile.locator("time").get_attribute("datetime")
   
    if not date_field or date_field.lower() == "null":
        return None
    
    try:
        parsed_date = datetime.strptime(date_field, "%Y-%m-%d").date()
        return (parsed_date - date.today()).days
    except ValueError:
        return None