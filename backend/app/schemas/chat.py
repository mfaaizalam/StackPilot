from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class PendingDraftTask(BaseModel):
    """A task currently drafted live on the board but not yet saved. The
    frontend sends the full current list of these on every chat request so
    the AI always knows exactly what's pending and can act on follow-up
    requests like 'make that one high priority' or 'drop the CI task'."""
    title: str
    description: str = ""
    priority: str = "medium"
    column_id: int
    column_name: str


class ChatRequest(BaseModel):
    message: str
    pending_tasks: list[PendingDraftTask] = []


class DraftTask(BaseModel):
    """A task the AI has drafted or revised. Not saved to the DB — the
    frontend renders these as unsaved draft cards and only persists them
    (via the normal POST /tasks/ endpoint) once the user confirms in chat."""
    title: str
    description: str = ""
    priority: str = "medium"
    column_id: int
    column_name: str


class ChatColumnAction(BaseModel):
    """A column created for real immediately (no draft step)."""
    id: int
    name: str


class ChatAction(BaseModel):
    """
    - "draft_tasks": the definitive, COMPLETE set of tasks that should now
      be pending on the board — this always replaces whatever was pending
      before, whether this is a brand-new single task, a whole-board build,
      or an edit to already-pending tasks (add/remove/change one of them).
      "columns" is only non-empty when new columns were needed for this set.
    - "create_column": a single column created for real immediately, with
      no tasks attached, after the user explicitly confirmed it in chat.
    """
    type: Literal["draft_tasks", "create_column"]
    columns: list[ChatColumnAction] = []
    tasks: list[DraftTask] = []
    column: Optional[ChatColumnAction] = None


class ChatResponse(BaseModel):
    role: str
    message: str
    action: Optional[ChatAction] = None

    class Config:
        from_attributes = True