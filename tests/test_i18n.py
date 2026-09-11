"""The index page's English/Turkish toggle: every string pair is present and
the English side actually stays in English (regression test for a mix-up
where a couple of labels were wired backwards)."""

from __future__ import annotations

from utilikit.i18n import CATEGORY_TR, ENDPOINT_TR, TOOL_TR, UI_TR
from utilikit.registry import catalog


def test_every_category_has_a_translation():
    for t in catalog():
        assert t.category in CATEGORY_TR, f"missing Turkish name for category {t.category!r}"


def test_every_tool_has_a_translation():
    for t in catalog():
        assert t.key in TOOL_TR, f"missing Turkish title/description for tool {t.key!r}"
        assert TOOL_TR[t.key]["title"] and TOOL_TR[t.key]["description"]


def test_every_endpoint_has_a_translation():
    for t in catalog():
        for e in t.endpoints:
            assert e.path in ENDPOINT_TR, f"missing Turkish summary for {e.method} {e.path}"


def test_index_page_carries_both_languages(client):
    html = client.get("/").text
    # a couple of load-bearing pairs, checked in the direction that matters:
    # the *visible* (data-en) text must stay English, data-tr must be Turkish.
    assert 'data-en="try &rarr;"' in html or 'data-en="try →"' in html
    assert f'data-tr="{UI_TR["try_label"]}"' in html
    assert 'data-en="e.g."' in html
    assert f'data-tr="{UI_TR["example_label"]}"' in html
    assert 'data-en="needs:"' in html
    # the tool titles/descriptions and category names both appear
    assert "Encoding, hashing" in html
    assert TOOL_TR["codec"]["title"] in html
    assert "Media" in html  # a category name with no HTML-escaped characters
    assert CATEGORY_TR["Media"] in html
