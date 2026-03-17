# hyperstate/forms.py
"""Helpers for form validation and resubmission with field-level errors.

When a form submission fails validation, the server should return the same
form action with:
- Submitted values preserved (so the user doesn't retype everything)
- `error` set on each failing field
- A flash summarizing the problem

This module provides helpers to make that pattern easy.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .fields import FormField
from .flash import Flash
from .sections import ActionSection


class FieldErrors:
    """Collects field-level validation errors and applies them to a form action.

    Usage:
        errors = FieldErrors()
        if not title.strip():
            errors.add("title", "Title cannot be empty.")
        if scheduled_date and scheduled_date < date.today():
            errors.add("scheduled_date", "Date cannot be in the past.")

        if errors:
            return errors.apply(create_action, submitted_values, status_code=422)
    """

    def __init__(self) -> None:
        self._errors: dict[str, str] = {}

    def add(self, field_name: str, message: str) -> None:
        """Add an error for a specific field. Last error wins if called twice."""
        self._errors[field_name] = message

    def __bool__(self) -> bool:
        return bool(self._errors)

    def __len__(self) -> int:
        return len(self._errors)

    @property
    def messages(self) -> dict[str, str]:
        return dict(self._errors)

    def apply(
        self,
        action: ActionSection,
        values: dict[str, Any] | None = None,
        flash_title: str = "Please fix the errors below.",
    ) -> tuple[ActionSection, Flash]:
        """Return a copy of the action with errors and values applied, plus a flash.

        Args:
            action: The original form action section.
            values: Submitted values to preserve (keyed by field name).
            flash_title: Summary message for the flash notification.

        Returns:
            Tuple of (action_with_errors, flash). Use these to build the response.
        """
        new_action = deepcopy(action)
        values = values or {}

        _apply_errors_to_fields(new_action.fields, self._errors, values)

        flash = Flash(type="error", title=flash_title)
        return new_action, flash


def _apply_errors_to_fields(
    fields: list[FormField],
    errors: dict[str, str],
    values: dict[str, Any],
) -> None:
    """Recursively apply errors and values to a field list."""
    for i, field in enumerate(fields):
        name = field.name
        # Set the submitted value so the user doesn't lose their input
        if name in values:
            fields[i] = field.model_copy(update={"value": values[name]})
            field = fields[i]
        # Set the error message if this field has one
        if name in errors:
            fields[i] = field.model_copy(update={"error": errors[name]})
            field = fields[i]
        # Recurse into group and repeatable fields
        if hasattr(field, "fields") and field.fields:
            _apply_errors_to_fields(field.fields, errors, values)
