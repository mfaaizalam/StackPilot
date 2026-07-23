import json
from google import genai

from app.core.config import settings
from app.prompts.chat_prompt import SYSTEM_PROMPT
from app.rag.retrieval_service import build_rag_context
from app.services.chat_service import save_message
from app.rag.chat_retrieval import retrieve_chat_memory
from app.models.column import BoardColumn

client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)

VALID_PRIORITIES = {"low", "medium", "high"}


def _clean_json(text: str) -> str:
    text = text.replace("```json", "").replace("```", "")
    return text.strip()


def _resolve_column(name_to_column: dict, column_name: str):
    """Exact match first (case sensitive), then case-insensitive fallback.
    Never fuzzy-matches beyond that — if the model didn't name a real
    column, this returns None and the caller drops the item rather than
    guessing which column it meant."""
    if not column_name:
        return None
    key = column_name.strip().lower()
    return name_to_column.get(key)


def ask_ai(
        db,
        board_id: int,
        user_id: int,
        user_message: str,
        pending_tasks=None,
):
    pending_tasks = pending_tasks or []

    # Save user's message
    save_message(
        db=db,
        board_id=board_id,
        user_id=user_id,
        role="user",
        message=user_message
    )

    chat_memory = retrieve_chat_memory(
        board_id=board_id,
        question=user_message
    )

    rag_context = build_rag_context(
        db=db,
        board_id=board_id,
        question=user_message
    )

    # The AI may only place tasks into one of these (plus any it creates in
    # this same turn) — passed verbatim so it can't drift from what's
    # actually on the board.
    columns = (
        db.query(BoardColumn)
        .filter(BoardColumn.board_id == board_id)
        .all()
    )
    columns_line = (
        ", ".join(f'"{c.name}"' for c in columns)
        if columns else "(this board has no columns yet)"
    )

    if pending_tasks:
        pending_lines = "\n".join(
            f'  - "{t.title}" (priority: {t.priority}, column: "{t.column_name}")'
            + (f" — {t.description}" if t.description else "")
            for t in pending_tasks
        )
    else:
        pending_lines = "  (none — nothing is currently pending)"

    prompt = f"""
    Current Project Context:
    {rag_context}

    Existing columns on this board (use these EXACT names for "column_name"):
    {columns_line}

    Currently pending (unsaved) tasks — these are drafted but not yet saved
    to the board. If the user is asking you to change, add to, or remove
    from this set, your "tasks" output must be the complete resulting list,
    not just the difference:
    {pending_lines}

    Relevant Previous Conversation:
    {chat_memory}

    Current user Question:
    {user_message}
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            SYSTEM_PROMPT,
            prompt
        ]
    )

    raw = (response.text or "").strip()
    reply_text = raw
    action_payload = None

    try:
        data = json.loads(_clean_json(raw))
        reply_text = str(data.get("reply") or "").strip() or "Done."
        action_data = data.get("action")

        if isinstance(action_data, dict):
            action_type = action_data.get("type")

            # ── Draft, edit, or clear the pending task batch ──────────────
            if action_type == "draft_tasks":
                requested_columns = action_data.get("columns") or []
                requested_tasks = action_data.get("tasks") or []

                # Seed with what already exists so we never create a
                # duplicate column, then create genuinely new ones.
                name_to_column = {c.name.lower(): c for c in columns}
                created_any = False

                for raw_name in requested_columns:
                    name = str(raw_name or "").strip()
                    if not name or name.lower() in name_to_column:
                        continue
                    new_column = BoardColumn(name=name, board_id=board_id)
                    db.add(new_column)
                    db.flush()  # assigns an id without ending the transaction
                    name_to_column[name.lower()] = new_column
                    created_any = True

                if created_any:
                    db.commit()
                    for c in name_to_column.values():
                        db.refresh(c)

                tasks_payload = []
                for raw_task in requested_tasks:
                    raw_task = raw_task or {}
                    title = str(raw_task.get("title") or "").strip()
                    matched_column = _resolve_column(
                        name_to_column, str(raw_task.get("column_name") or "")
                    )

                    priority = str(raw_task.get("priority") or "medium").strip().lower()
                    if priority not in VALID_PRIORITIES:
                        priority = "medium"

                    if title and matched_column:
                        tasks_payload.append({
                            "title": title,
                            "description": str(raw_task.get("description") or ""),
                            "priority": priority,
                            "column_id": matched_column.id,
                            "column_name": matched_column.name,
                        })
                    # A task naming a column outside this turn's own list is
                    # silently dropped — the model broke the contract.

                # An explicit empty "tasks" list is a valid, intentional
                # result (e.g. "clear everything"), so this action is always
                # set once the model committed to draft_tasks — never gated
                # on tasks_payload being non-empty.
                action_payload = {
                    "type": "draft_tasks",
                    "columns": [
                        {"id": c.id, "name": c.name}
                        for c in name_to_column.values()
                    ],
                    "tasks": tasks_payload,
                }

            # ── Create a real column immediately (user already confirmed) ──
            elif action_type == "create_column":
                col_name = str(action_data.get("column_name") or "").strip()
                already_exists = any(
                    c.name.lower() == col_name.lower() for c in columns
                )

                if col_name and not already_exists:
                    new_column = BoardColumn(name=col_name, board_id=board_id)
                    db.add(new_column)
                    db.commit()
                    db.refresh(new_column)
                    action_payload = {
                        "type": "create_column",
                        "column": {
                            "id": new_column.id,
                            "name": new_column.name,
                        }
                    }
                # Already exists or empty name → no action, reply stands alone.

    except (json.JSONDecodeError, AttributeError, TypeError):
        # Model didn't follow the JSON contract this turn — degrade
        # gracefully to a plain-text reply instead of a 500.
        reply_text = raw
        action_payload = None

    # Save AI's reply as plain text only, so RAG/chat-memory embeddings
    # stay clean and never contain raw JSON.
    save_message(
        db=db,
        board_id=board_id,
        user_id=user_id,
        role="assistant",
        message=reply_text
    )

    return {
        "message": reply_text,
        "action": action_payload
    }