"""Tiny, idempotent schema upgrade for columns added after the first deploy.

`Base.metadata.create_all` only creates MISSING TABLES. It never adds a column to a table
that already exists, so on the live Neon database every query on `tasks` would fail with
"column tasks.requirement_id does not exist" the moment Phase 4 code is deployed.
This adds the missing columns once; running it again does nothing.

Alembic is still the right long-term tool (see the build plan); this covers the one
table that changed so the exhibition deploy cannot break.
"""
import logging

from sqlalchemy import inspect, text

log = logging.getLogger("stackpilot.migrate")

# column name -> SQL type (portable across PostgreSQL and SQLite)
TASK_COLUMNS = {
    "requirement_id": "VARCHAR(40)",
    "estimate_points": "INTEGER",
    "depends_on": "JSON",
    "srs_id": "INTEGER",
}


def ensure_task_columns(engine) -> list[str]:
    """Add any missing Phase 4 columns to `tasks`. Returns the names that were added."""
    insp = inspect(engine)
    if "tasks" not in insp.get_table_names():
        return []  # fresh database: create_all already built the full table
    existing = {c["name"] for c in insp.get_columns("tasks")}
    added: list[str] = []
    with engine.begin() as conn:
        for name, ddl in TASK_COLUMNS.items():
            if name in existing:
                continue
            if engine.dialect.name == "postgresql":
                # IF NOT EXISTS makes two servers starting at the same time safe
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS {name} {ddl}"))
            else:
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {name} {ddl}"))
            added.append(name)
    if added:
        log.warning("Added columns to tasks: %s", ", ".join(added))
    return added
