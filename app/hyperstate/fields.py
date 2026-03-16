from __future__ import annotations
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Field dependency model
# ──────────────────────────────────────────────

class DependsOn(BaseModel):
    """Declares that this field depends on other fields' values.

    The client's only job is:
    1. Watch the named fields for changes
    2. Interpolate {field_name} tokens in the URL
    3. Fetch and replace (options, field def, or entire form)
    """
    fields: list[str]
    behavior: Literal["reload_options", "reload_field", "reload_form"]
    options_href: str | None = None    # for reload_options
    field_href: str | None = None      # for reload_field
    clear_on_change: bool = True


# ──────────────────────────────────────────────
# Field option (for select, radio, multi_select)
# ──────────────────────────────────────────────

class FieldOption(BaseModel):
    value: str
    label: str
    disabled: bool = False
    description: str | None = None     # shown as sublabel


# ──────────────────────────────────────────────
# Validation rules
# ──────────────────────────────────────────────

class ValidationRules(BaseModel):
    min_length: int | None = None
    max_length: int | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    pattern: str | None = None
    pattern_description: str | None = None  # human-readable regex explanation


# ──────────────────────────────────────────────
# Base field with common attributes
# ──────────────────────────────────────────────

class FieldBase(BaseModel):
    name: str
    label: str
    required: bool = False
    value: Any = None
    default: Any = None
    disabled: bool = False
    readonly: bool = False
    hidden: bool = False
    placeholder: str | None = None
    help: str | None = None
    error: str | None = None
    depends_on: DependsOn | None = None
    span: int | None = None            # column span in grid layout


# ──────────────────────────────────────────────
# Concrete field types
# ──────────────────────────────────────────────

class TextField(FieldBase):
    type: Literal["text"] = "text"
    validation: ValidationRules | None = None


class TextareaField(FieldBase):
    type: Literal["textarea"] = "textarea"
    rows: int = 4
    validation: ValidationRules | None = None


class NumberField(FieldBase):
    type: Literal["number"] = "number"
    validation: ValidationRules | None = None


class CurrencyField(FieldBase):
    type: Literal["currency"] = "currency"
    currency: str = "USD"
    validation: ValidationRules | None = None


class BooleanField(FieldBase):
    type: Literal["boolean"] = "boolean"


class SelectField(FieldBase):
    type: Literal["select"] = "select"
    options: list[FieldOption] = []
    options_href: str | None = None    # lazy-load options from server


class MultiSelectField(FieldBase):
    type: Literal["multi_select"] = "multi_select"
    options: list[FieldOption] = []
    options_href: str | None = None


class RadioField(FieldBase):
    type: Literal["radio"] = "radio"
    options: list[FieldOption] = []


class DateField(FieldBase):
    type: Literal["date"] = "date"
    validation: ValidationRules | None = None


class DatetimeField(FieldBase):
    type: Literal["datetime"] = "datetime"
    validation: ValidationRules | None = None


class EmailField(FieldBase):
    type: Literal["email"] = "email"
    validation: ValidationRules | None = None


class UrlField(FieldBase):
    type: Literal["url"] = "url"
    validation: ValidationRules | None = None


class PhoneField(FieldBase):
    type: Literal["phone"] = "phone"
    validation: ValidationRules | None = None


class FileField(FieldBase):
    type: Literal["file"] = "file"
    accept: list[str] = []             # MIME types
    max_size_mb: float | None = None


class HiddenField(FieldBase):
    type: Literal["hidden"] = "hidden"
    label: str = ""                    # override: hidden fields don't need labels


class GroupField(FieldBase):
    """A fieldset containing nested fields."""
    type: Literal["group"] = "group"
    layout: Literal["stack", "columns"] = "stack"
    fields: list[FormField]


class RepeatableField(FieldBase):
    """Dynamic list of field groups (line items, addresses, etc.)."""
    type: Literal["repeatable"] = "repeatable"
    fields: list[FormField]            # template for each row
    items: list[dict[str, Any]] = []   # current data
    min_items: int = 0
    max_items: int | None = None


# ──────────────────────────────────────────────
# The discriminated union
# ──────────────────────────────────────────────

FormField = Annotated[
    TextField
    | TextareaField
    | NumberField
    | CurrencyField
    | BooleanField
    | SelectField
    | MultiSelectField
    | RadioField
    | DateField
    | DatetimeField
    | EmailField
    | UrlField
    | PhoneField
    | FileField
    | HiddenField
    | GroupField
    | RepeatableField,
    Field(discriminator="type"),
]

# Rebuild for recursive types
GroupField.model_rebuild()
RepeatableField.model_rebuild()
