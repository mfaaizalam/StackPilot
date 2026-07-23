from pydantic import BaseModel


class NextAction(BaseModel):
    action: str
    reason: str


class DuplicateGroup(BaseModel):
    titles: list[str]
    note: str


class BreakdownSuggestion(BaseModel):
    task_title: str
    subtasks: list[str] = []
    # Resolved server-side (not by the AI) so the frontend can act on it
    # directly — e.g. to create the subtasks for real.
    task_id: int | None = None
    column_id: int | None = None


class AiInsightsFields(BaseModel):
    """What Gemini is asked to produce."""
    digest: str
    next_action: NextAction
    stuck_points: list[str] = []
    duplicates: list[DuplicateGroup] = []
    breakdowns: list[BreakdownSuggestion] = []


class ProjectInsightsResponse(BaseModel):
    """Full response sent to the frontend — AI fields plus stats computed
    directly from the database."""
    board_name: str
    digest: str
    next_action: NextAction
    stuck_points: list[str] = []
    duplicates: list[DuplicateGroup] = []
    breakdowns: list[BreakdownSuggestion] = []
    total_columns: int
    total_tasks: int
    completion_percent: float
    priority_breakdown: dict[str, int] = {}
