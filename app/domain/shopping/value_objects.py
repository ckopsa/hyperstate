from __future__ import annotations

import re
from dataclasses import dataclass

# A leading amount (integer, decimal, or simple fraction) followed by an
# optional unit: "1 lb", "24 oz", "1/2 cup", "2", "1 head". Anything that does
# not start with a number is treated as a unit-only quantity ("a pinch").
_AMOUNT = re.compile(r"^\s*(\d+(?:\.\d+)?(?:\s*/\s*\d+)?)\s*(.*)$")


@dataclass(frozen=True)
class Quantity:
    """A parsed ingredient amount: a numeric ``amount`` plus a free-text ``unit``.

    Recipe ingredient quantities are stored as loose strings ("1 lb", "2 cups",
    "a pinch"). To roll them up on a shopping list we split each into a numeric
    ``amount`` and a ``unit`` so that two lines sharing the same (name, unit)
    can be summed. ``amount`` is ``None`` when no leading number was present.
    """

    amount: float | None = None
    unit: str = ""

    @classmethod
    def parse(cls, raw: str | None) -> "Quantity":
        if raw is None:
            return cls(amount=None, unit="")
        text = raw.strip()
        if not text:
            return cls(amount=None, unit="")
        match = _AMOUNT.match(text)
        if not match:
            # No leading number — keep the whole string as the unit ("a pinch").
            return cls(amount=None, unit=text)
        return cls(amount=_to_float(match.group(1)), unit=match.group(2).strip())

    def added_to(self, other: "Quantity") -> "Quantity":
        """Combine two quantities of the same unit, summing numeric amounts.

        A ``None`` amount contributes nothing to the sum but does not erase a
        sibling's number: "1 lb" + (unspecified) "lb" stays "1 lb". Only when
        *every* contribution is ``None`` does the result stay ``None``.
        """
        if self.amount is None and other.amount is None:
            return Quantity(amount=None, unit=self.unit)
        total = (self.amount or 0.0) + (other.amount or 0.0)
        return Quantity(amount=total, unit=self.unit)

    @property
    def label(self) -> str | None:
        """Human-readable rendering, or ``None`` when there is nothing to show."""
        if self.amount is None:
            return self.unit or None
        number = f"{self.amount:g}"  # 2.0 -> "2", 0.5 -> "0.5", 1.5 -> "1.5"
        return f"{number} {self.unit}".strip()


def _to_float(token: str) -> float:
    token = token.strip()
    if "/" in token:
        numerator, _, denominator = token.partition("/")
        return float(numerator) / float(denominator)
    return float(token)
