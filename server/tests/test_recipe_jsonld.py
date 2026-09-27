"""Schema.org JSON-LD ingredient parsing for URL import."""

from app.scripts.extract import parse_recipe_jsonld_ingredients


def test_parse_recipe_jsonld_single_recipe():
    html = """
    <html><head>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Recipe",
      "name": "Salted Caramel",
      "recipeIngredient": [
        "1 cup (200g) granulated sugar",
        "6 Tablespoons (85g) unsalted butter",
        "1/2 cup (120g/ml) heavy cream",
        "1 teaspoon salt"
      ]
    }
    </script></head><body></body></html>
    """
    lines = parse_recipe_jsonld_ingredients(html)
    assert len(lines) == 4
    assert "granulated sugar" in lines[0]
    assert "unsalted butter" in lines[1]
    assert "heavy cream" in lines[2]
    assert lines[3] == "1 teaspoon salt"


def test_parse_recipe_jsonld_graph():
    html = """
    <script type='application/ld+json'>
    {"@graph": [
      {"@type": "WebPage", "name": "Blog"},
      {"@type": "Recipe", "recipeIngredient": ["2 eggs", "1 cup flour"]}
    ]}
    </script>
    """
    lines = parse_recipe_jsonld_ingredients(html)
    assert lines == ["2 eggs", "1 cup flour"]


def test_parse_recipe_jsonld_missing_returns_empty():
    assert parse_recipe_jsonld_ingredients("<html><body>No schema</body></html>") == []
