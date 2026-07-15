"""Unit tests for index-slide reflow helpers."""

from types import SimpleNamespace

from scripts.update_delivery_status import INDEX_ENTRY_RULES


def test_index_entry_rules_cover_all_delivery_services():
    delivery_titles = {
        rule[1]
        for rule in INDEX_ENTRY_RULES
        if rule[2]
    }
    expected = {
        "Cost Core Service",
        "Supplier Core Service",
        "Pricing Core Service",
        "Wentworth",
        "Location Core Service",
        "Pharmacy and Wellness",
        "Global Sourcing Solution",
        "LoCo",
    }
    assert expected <= delivery_titles


def test_cell_has_index_content_detects_loco_label():
    from scripts.update_delivery_status import _cell_has_index_content

    cell = SimpleNamespace(
        text_frame=SimpleNamespace(
            text="LoCo (BSA)",
            paragraphs=[],
        )
    )
    assert _cell_has_index_content(cell)
