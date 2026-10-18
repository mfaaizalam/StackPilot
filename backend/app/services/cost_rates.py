"""Loads and validates the Pakistan rate table (app/data/pk_rates.json).

Golden rule 7: rates come from this maintained file, never from the AI. Edit the JSON,
restart (or just call again: the file is re-read on every request, it is tiny)."""
import json
from pathlib import Path

from app.schemas.cost import RatesTable

RATES_PATH = Path(__file__).resolve().parent.parent / "data" / "pk_rates.json"
SCENARIOS = ("optimistic", "likely", "pessimistic")


class RatesError(Exception):
    pass


def validate_rates(data: dict) -> RatesTable:
    try:
        table = RatesTable.model_validate(data)
    except Exception as e:  # pydantic ValidationError -> readable message
        raise RatesError(f"Rate table is invalid: {e}") from e
    if set(table.scenarios) != set(SCENARIOS):
        raise RatesError("Rate table must define exactly the scenarios: optimistic, likely, pessimistic.")
    total = sum(r.allocation for r in table.roles.values())
    if abs(total - 1.0) > 1e-6:
        raise RatesError(f"Role allocations must add up to 1.0 (they add up to {total:.3f}).")
    for rid, r in table.roles.items():
        if r.monthly_min > r.monthly_max:
            raise RatesError(f"Role '{rid}': monthly_min is larger than monthly_max.")
    for need in ("web",):
        if need not in table.model.platform_multiplier:
            raise RatesError(f"platform_multiplier must include '{need}'.")
    return table


def load_rates(path: Path | None = None) -> RatesTable:
    p = path or RATES_PATH
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise RatesError(f"Could not read the rate table: {e}") from e
    return validate_rates(data)


def unverified_items(t: RatesTable) -> list[str]:
    """Names of every rate that still has verified=false (shown as a warning in the UI)."""
    out: list[str] = []
    out += [r.label for r in t.roles.values() if not r.verified]
    out += [o.label for o in t.overheads if not o.verified]
    out += [m.label for m in t.monthly_costs if not m.verified]
    out += [o.label for o in t.one_time_costs if not o.verified]
    for x in (t.contingency, t.tax):
        if not x.verified:
            out.append(x.label)
    if not t.maintenance.verified:
        out.append(t.maintenance.label)
    return out
