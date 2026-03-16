from pydantic import BaseModel
from .fields import FieldOption, FormField


class OptionsResponse(BaseModel):
    """Returned by options_href endpoints."""
    options: list[FieldOption]


class FieldResponse(BaseModel):
    """Returned by field_href endpoints — a complete replacement field definition."""
    field: FormField
