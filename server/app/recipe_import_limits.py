import os

ACTIVE_IMPORT_STATUSES = ("queued", "running", "ai_wait", "ready")
DUPLICATE_BLOCK_STATUSES = ACTIVE_IMPORT_STATUSES

PIPELINE_LABELS = {
    1: "Reaching browser",
    2: "Retrieving data",
    3: "Extraction via AI",
}

AI_BACKOFF_SECONDS = (300, 600, 1200)


def max_active_imports() -> int:
    raw = os.getenv("RECIPE_IMPORT_MAX_ACTIVE", "25")
    try:
        return max(1, int(raw))
    except ValueError:
        return 25


def pipeline_label(step: int | None) -> str | None:
    if step is None:
        return None
    return PIPELINE_LABELS.get(step)


def is_retryable_gemini_error(message: str) -> bool:
    lower = message.lower()
    if any(token in lower for token in ("503", "429", "unavailable", "resource exhausted")):
        return True
    if "high demand" in lower:
        return True
    return False


def ai_backoff_seconds(attempt_count: int) -> int | None:
    if attempt_count < 0 or attempt_count >= len(AI_BACKOFF_SECONDS):
        return None
    return AI_BACKOFF_SECONDS[attempt_count]
