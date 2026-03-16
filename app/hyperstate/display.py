from typing import Literal, Any
from pydantic import BaseModel


class DisplayHint(BaseModel):
    """Tells the client HOW to format a value, not what the value is."""
    display: Literal[
        "plain", "badge", "currency", "datetime", "date",
        "percentage", "number", "link", "code", "markdown"
    ] = "plain"
    variant: str | None = None        # for badge: "success", "warning", "danger"
    currency: str | None = None       # for currency: "USD", "EUR"
    format: str | None = None         # for datetime: "relative", "short", "long"


class PropertyItem(DisplayHint):
    """A single key-value pair in a properties section."""
    key: str
    label: str
    value: Any
    href: str | None = None           # makes the value a navigable link
