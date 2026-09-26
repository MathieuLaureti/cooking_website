from app.scripts.extract import _looks_like_bot_wall, _page_text_usable


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
