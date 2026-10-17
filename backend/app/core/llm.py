"""The ONLY place that talks to the LLM.

    llm_json(prompt, SomeSchema)  ->  validated SomeSchema instance

Everything else (SRS, diagrams, board generation, costing) goes through here,
so the model name, retries and fake/offline mode live in one file.
"""
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)

_RETRYABLE = ("429", "500", "502", "503", "504", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "DEADLINE", "INTERNAL")
_client = None


class LLMError(Exception):
    """Raised with a message that is safe to show to the user."""


def _get_client():
    global _client
    if _client is None:
        from google import genai  # imported lazily so tests/fake mode need no network libs
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _sleep(seconds: float) -> None:  # separate function so tests can patch it
    time.sleep(seconds)


def llm_json(
    prompt: str,
    schema: type[T],
    *,
    system: str = "",
    temperature: float = 0.2,
    max_attempts: int = 3,
) -> T:
    if settings.LLM_FAKE == "1":
        from app.core.llm_fake import fake_response
        return fake_response(schema)

    from google.genai import types

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema,
        temperature=temperature,
        system_instruction=system or None,
    )

    last_error = ""
    for attempt in range(1, max_attempts + 1):
        try:
            response = _get_client().models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
            text = (response.text or "").strip()
            if not text:
                raise ValueError("empty response")
            return schema.model_validate_json(text)
        except ValidationError as e:
            last_error = "The AI returned data in the wrong shape."
            # a malformed answer is worth one more try, no need to wait long
            if attempt < max_attempts:
                _sleep(1)
        except Exception as e:  # network / quota / server errors
            msg = str(e)
            last_error = msg[:200]
            if any(code in msg for code in _RETRYABLE) and attempt < max_attempts:
                _sleep(2 ** attempt)  # 2s, 4s
                continue
            if attempt < max_attempts and isinstance(e, ValueError):
                _sleep(1)
                continue
            break
    raise LLMError(f"The AI service could not complete the request. {last_error}".strip())
