from typing import Literal
from pydantic import BaseModel


class Flash(BaseModel):
    type: Literal["success", "warning", "error", "info"]
    title: str
    body: str | None = None
