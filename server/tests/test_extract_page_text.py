import pytest

from app.scripts.extract import (
    RecipeExtractor,
    _format_fetch_errors,
    _looks_like_bot_wall,
    _page_text_usable,
)


def test_bot_wall_phrase_detected():
    text = "sallysbakingaddiction.com Performing security verification"
    assert _looks_like_bot_wall(text)


def test_page_text_usable_rejects_short_body():
    assert not _page_text_usable("a" * 100)


def test_page_text_usable_rejects_cloudflare_challenge():
    challenge = (
        "Performing security verification. "
        "Enable JavaScript and cookies to continue. " + ("x" * 400)
    )
    assert not _page_text_usable(challenge)


def test_page_text_usable_accepts_long_recipe_like_text():
    body = "Homemade caramel\n" + ("granulated sugar and butter. " * 30)
    assert _page_text_usable(body)


def test_format_fetch_errors_includes_both_sources():
    detail = _format_fetch_errors(
        "Extracted text too short.",
        "Reader fallback HTTP 503",
    )
    assert "Extracted text too short." in detail
    assert "Reader fallback HTTP 503" in detail


@pytest.mark.asyncio
async def test_fetch_text_retries_reader_then_succeeds(monkeypatch):
    calls = {"n": 0}
    good = "Homemade caramel\n" + ("granulated sugar and butter. " * 30)

    async def fake_playwright(self, url: str) -> str:
        return "Performing security verification"

    async def fake_reader(url: str) -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("Reader fallback text too short.")
        return good

    monkeypatch.setattr(RecipeExtractor, "_fetch_text_playwright", fake_playwright)
    monkeypatch.setattr(
        "app.scripts.extract._fetch_reader_fallback",
        fake_reader,
    )
    async def noop_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr("app.scripts.extract.asyncio.sleep", noop_sleep)

    text = await RecipeExtractor()._fetch_text("https://example.com/recipe")
    assert text == good
    assert calls["n"] == 2
