"""Who did what, per board.

Best-effort: logging must never break the real action. It writes through its OWN short
session so the caller's objects are not expired by a commit (an expired ORM object would
be serialised as `{}` by FastAPI). The `db` argument is kept only so call sites read naturally.
"""
import logging

from app.core.database import SessionLocal
from app.models.rbac import BoardActivity

log = logging.getLogger("stackpilot.activity")


def log_activity(db, board_id: int, user_id: int | None, action: str, summary: str,
                 entity_type: str | None = None, entity_id: int | None = None) -> None:
    s = SessionLocal()
    try:
        s.add(BoardActivity(board_id=board_id, user_id=user_id, action=action,
                            summary=(summary or "")[:500], entity_type=entity_type,
                            entity_id=entity_id))
        s.commit()
    except Exception:
        s.rollback()
        log.exception("Could not write activity log")
    finally:
        s.close()