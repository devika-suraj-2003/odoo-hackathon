from datetime import date, timedelta
from calendar import monthrange


def get_next_billing_date(current_date: date, billing_period: str) -> date:
    """Calculate the next billing date."""

    if billing_period == "daily":
        return current_date + timedelta(days=1)

    if billing_period == "weekly":
        return current_date + timedelta(weeks=1)

    if billing_period == "monthly":
        year = current_date.year + (current_date.month // 12)
        month = (current_date.month % 12) + 1
        day = min(current_date.day, monthrange(year, month)[1])
        return date(year, month, day)

    if billing_period == "yearly":
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            # Handles February 29 in a non-leap year.
            return current_date.replace(
                year=current_date.year + 1,
                day=28
            )

    raise ValueError(f"Unsupported billing period: {billing_period}")


def calculate_billing_period(
    start_date: date,
    billing_period: str
) -> tuple[date, date]:
    """Return the start and end dates of a billing period."""

    next_date = get_next_billing_date(start_date, billing_period)
    return start_date, next_date - timedelta(days=1)