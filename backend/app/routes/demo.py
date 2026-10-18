"""Read-only, prebuilt exhibition examples. Contains no user data or secrets."""
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/demo", tags=["Exhibition demo"])
_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "data" / "demo_fixtures.json"
_ALLOWED = {"hospital", "ecommerce", "university"}

@router.get("/{name}")
def get_demo(name: str):
    """Return a static, instantly available fixture without calling the database or an LLM."""
    if name not in _ALLOWED:
        raise HTTPException(status_code=404, detail="Demo not found. Choose hospital, ecommerce, or university.")
    try:
        fixtures = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
        return fixtures[name]
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="The offline demo is temporarily unavailable. Please contact the presenter.")
