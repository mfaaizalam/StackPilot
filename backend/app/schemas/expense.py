from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

CATEGORY = Literal["labour", "infrastructure", "tools", "licences", "travel", "training", "contingency", "other"]


def _money(**kw):
    return Field(max_digits=14, decimal_places=2, **kw)


class ExpenseCreate(BaseModel):
    category: CATEGORY
    description: str = Field(min_length=1, max_length=300)
    estimated_amount: Decimal = _money(ge=0, default=Decimal(0))
    actual_amount: Decimal = _money(ge=0, default=Decimal(0))
    incurred_on: date | None = None
    activity_id: int | None = None


class ExpenseUpdate(BaseModel):
    category: CATEGORY | None = None
    description: str | None = Field(default=None, min_length=1, max_length=300)
    estimated_amount: Decimal | None = _money(ge=0, default=None)
    actual_amount: Decimal | None = _money(ge=0, default=None)
    incurred_on: date | None = None
    activity_id: int | None = None
    clear_activity: bool = False     # true = make it a project-level expense
