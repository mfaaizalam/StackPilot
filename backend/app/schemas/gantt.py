from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Money = Decimal
STATUS = Literal["planned", "approved", "disbursed"]


def _money(**kw):
    return Field(max_digits=14, decimal_places=2, **kw)


class ActivityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phase: str | None = Field(default=None, max_length=100)
    start_date: date
    end_date: date
    planned_hours: Money = _money(ge=0, default=Decimal(0))
    actual_hours: Money = _money(ge=0, default=Decimal(0))
    progress_pct: int = Field(default=0, ge=0, le=100)
    estimated_cost: Money = _money(ge=0, default=Decimal(0))
    actual_cost: Money = _money(ge=0, default=Decimal(0))
    depends_on: list[int] = Field(default_factory=list, max_length=50)
    task_id: int | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before the start date.")
        return self


class ActivityUpdate(BaseModel):
    """Every field optional (PATCH). Date order is re-checked in the service against the stored row."""
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phase: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    planned_hours: Money | None = _money(ge=0, default=None)
    actual_hours: Money | None = _money(ge=0, default=None)
    progress_pct: int | None = Field(default=None, ge=0, le=100)
    estimated_cost: Money | None = _money(ge=0, default=None)
    actual_cost: Money | None = _money(ge=0, default=None)
    depends_on: list[int] | None = Field(default=None, max_length=50)


class IncrementCreate(BaseModel):
    amount: Money = _money(gt=0)
    effective_date: date
    status: STATUS = "planned"
    activity_id: int | None = None
    phase: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=300)


class IncrementUpdate(BaseModel):
    amount: Money | None = _money(gt=0, default=None)
    effective_date: date | None = None
    status: STATUS | None = None
    activity_id: int | None = None
    phase: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=300)
    clear_target: bool = False   # true = detach from the activity/phase (project-wide increment)


class BudgetUpdate(BaseModel):
    base_budget: Money = _money(ge=0)


class SeedRequest(BaseModel):
    mode: Literal["create", "sync"] = "create"
