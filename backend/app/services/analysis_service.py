import json
from google import genai

from app.core.config import settings
from app.prompts.analysis_prompt import SYSTEM_PROMPT
from app.schemas.analysis import AiInsightsFields, ProjectInsightsResponse, BreakdownSuggestion
from app.models.board import Board
from app.models.column import BoardColumn
from app.models.task import Task

client = genai.Client(
    api_key=settings.GEMINI_API_KEY_2
)

DONE_KEYWORDS = ("done", "complete", "completed", "deployed", "shipped", "live", "released")


def _clean_json(text: str) -> str:
    text = text.replace("```json", "").replace("```", "")
    return text.strip()


def _compute_stats(columns: list[BoardColumn], tasks: list[Task]) -> dict:
    total_tasks = len(tasks)
    total_columns = len(columns)

    done_column_ids = {
        c.id for c in columns
        if any(kw in (c.name or "").lower() for kw in DONE_KEYWORDS)
    }
    done_count = sum(1 for t in tasks if t.column_id in done_column_ids)
    completion_percent = round((done_count / total_tasks) * 100, 1) if total_tasks else 0.0

    priority_breakdown = {"high": 0, "medium": 0, "low": 0}
    for t in tasks:
        p = (t.priority or "low").lower()
        if p not in priority_breakdown:
            priority_breakdown[p] = 0
        priority_breakdown[p] += 1

    tasks_per_column = {}
    for c in columns:
        tasks_per_column[c.name] = sum(1 for t in tasks if t.column_id == c.id)

    return {
        "total_tasks": total_tasks,
        "total_columns": total_columns,
        "completion_percent": completion_percent,
        "priority_breakdown": priority_breakdown,
        "tasks_per_column": tasks_per_column,
    }


def _build_context(board: Board, columns: list[BoardColumn], tasks: list[Task], stats: dict) -> str:
    lines = [
        f"Board name: {board.name}",
        f"Board description: {board.description or '(none provided)'}",
        "",
        f"Total columns: {stats['total_columns']}",
        f"Total tasks: {stats['total_tasks']}",
        f"Computed completion: {stats['completion_percent']}%",
        f"Priority breakdown: {stats['priority_breakdown']}",
        "",
        "Tasks per column:",
    ]
    for name, count in stats["tasks_per_column"].items():
        lines.append(f"- {name}: {count} task(s)")

    lines.append("")
    lines.append("Task detail:")
    if tasks:
        for t in tasks:
            col_name = next((c.name for c in columns if c.id == t.column_id), "Unknown")
            lines.append(f"- [{col_name}] ({t.priority or 'low'}) {t.title}: {t.description or 'no description'}")
    else:
        lines.append("- (no tasks yet)")

    return "\n".join(lines)


def _resolve_breakdown_ids(breakdowns: list[BreakdownSuggestion], tasks: list[Task]) -> list[BreakdownSuggestion]:
    """Match the AI's task_title back to a real DB task so the frontend can
    act on it (e.g. actually create the subtasks). Exact match first, then
    case-insensitive. If nothing matches, task_id/column_id stay None and
    the frontend just shows the suggestion without an "apply" action."""
    by_title = {t.title: t for t in tasks}
    by_title_lower = {t.title.strip().lower(): t for t in tasks}

    resolved = []
    for b in breakdowns:
        match = by_title.get(b.task_title) or by_title_lower.get(b.task_title.strip().lower())
        if match:
            b.task_id = match.id
            b.column_id = match.column_id
        resolved.append(b)
    return resolved


def analyze_project(db, board_id: int) -> ProjectInsightsResponse:
    board = db.query(Board).filter(Board.id == board_id).first()
    if not board:
        raise ValueError("Board not found.")

    columns = db.query(BoardColumn).filter(BoardColumn.board_id == board_id).all()
    tasks = (
        db.query(Task)
        .join(BoardColumn)
        .filter(BoardColumn.board_id == board_id)
        .all()
    )

    stats = _compute_stats(columns, tasks)
    context = _build_context(board, columns, tasks, stats)

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[SYSTEM_PROMPT, context],
    )

    try:
        cleaned = _clean_json(response.text)
        data = json.loads(cleaned)
        ai_fields = AiInsightsFields.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        raise ValueError("StackPilot AI returned an invalid analysis. Please try again.")

    resolved_breakdowns = _resolve_breakdown_ids(ai_fields.breakdowns, tasks)

    return ProjectInsightsResponse(
        board_name=board.name,
        digest=ai_fields.digest,
        next_action=ai_fields.next_action,
        stuck_points=ai_fields.stuck_points,
        duplicates=ai_fields.duplicates,
        breakdowns=resolved_breakdowns,
        total_columns=stats["total_columns"],
        total_tasks=stats["total_tasks"],
        completion_percent=stats["completion_percent"],
        priority_breakdown=stats["priority_breakdown"],
    )
