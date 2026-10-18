from typing import Literal

from pydantic import BaseModel, Field

Level = Literal["low", "nominal", "high"]


class CostRequest(BaseModel):
    srs_id: int | None = None  # default: latest SRS version of the board
    platform: Literal["web", "desktop", "mobile", "web_mobile"] = "web"
    complexity: Level = "nominal"        # COCOMO II CPLX
    team_experience: Level = "nominal"   # COCOMO II PCAP/APEX (low experience = more effort)
    reliability: Level = "nominal"       # COCOMO II RELY
    expected_annual_revenue: float | None = Field(default=None, ge=0, le=1e12)  # PKR / year, optional
    horizon_years: int = Field(default=3, ge=1, le=10)


# ---- what the AI returns (flat, no numbers of its own) ----
class CostExplanation(BaseModel):
    summary: str
    key_drivers: list[str]
    risks: list[str]
    tips: list[str]


# ---- the rate table (validated when loaded) ----
class RateItem(BaseModel):
    source: str
    last_updated: str
    verified: bool = False


class RoleRate(RateItem):
    label: str
    monthly_min: float = Field(gt=0)
    monthly_max: float = Field(gt=0)
    allocation: float = Field(ge=0, le=1)


class PctItem(RateItem):
    id: str = ""
    label: str
    pct: float = Field(ge=0, le=1)


class MonthlyCost(RateItem):
    id: str
    label: str
    pkr_per_month: float = Field(ge=0)
    per_head: bool = False


class OneTimeCost(RateItem):
    id: str
    label: str
    pkr: float = Field(ge=0)


class Scenario(BaseModel):
    label: str
    effort_factor: float = Field(gt=0)
    salary_point: float = Field(ge=0, le=1)


class ModelParams(BaseModel):
    loc_per_function_point: float = Field(gt=0)
    hours_per_person_month: float = Field(gt=0)
    ucp_hours_per_point: float = Field(gt=0)
    platform_multiplier: dict[str, float]


class Maintenance(RateItem):
    label: str
    annual_pct_of_build: float = Field(ge=0, le=1)


class RatesMeta(BaseModel):
    currency: str
    version: str
    last_updated: str
    notes: str = ""


class RatesTable(BaseModel):
    meta: RatesMeta
    scenarios: dict[str, Scenario]
    model: ModelParams
    roles: dict[str, RoleRate]
    overheads: list[PctItem]
    monthly_costs: list[MonthlyCost]
    one_time_costs: list[OneTimeCost]
    contingency: PctItem
    tax: PctItem
    maintenance: Maintenance
