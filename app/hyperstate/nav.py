from pydantic import BaseModel


class NavLink(BaseModel):
    label: str
    href: str
    rel: str | None = None
    type: str | None = None  # e.g., "application/pdf" for downloads
