from datetime import date, datetime
from bs4 import Tag


def get_item_delivery_lead_time(tile: Tag):
    time_tag = tile.select_one("time")
    date_field = time_tag.get("datetime") if time_tag else None
    target_date = datetime.strptime(str(date_field), "%Y-%m-%d").date() if date_field else None

    if not target_date:
        return None

    # Today's date
    today = date.today()

    # Difference in days
    return (target_date - today).days
