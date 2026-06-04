"""Helpers for safe marking-code display in UI widgets."""

from __future__ import annotations


def format_marking_code_for_display(code: str | None, *, empty: str = "-") -> str:
    """Return scanner code with visible control-character markers."""

    if not code:
        return empty
    return (
        str(code)
        .strip()
        .replace("\x1d", "<GS>")
        .replace("\r", "<CR>")
        .replace("\n", "<LF>")
        .replace("\t", "<TAB>")
    )
