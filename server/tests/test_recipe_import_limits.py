from app.recipe_import_limits import (
    ai_backoff_seconds,
    is_retryable_gemini_error,
    pipeline_label,
)


def test_pipeline_labels():
    assert pipeline_label(1) == "Reaching browser"
    assert pipeline_label(3) == "Extraction via AI"


def test_retryable_gemini_errors():
    assert is_retryable_gemini_error('{"error":{"code":503,"status":"UNAVAILABLE"}}')
    assert not is_retryable_gemini_error("Extracted text too short")


def test_ai_backoff_sequence():
    assert ai_backoff_seconds(0) == 300
    assert ai_backoff_seconds(1) == 600
    assert ai_backoff_seconds(2) == 1200
    assert ai_backoff_seconds(3) is None
