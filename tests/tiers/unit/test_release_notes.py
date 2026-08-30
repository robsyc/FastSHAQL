"""Unit tests for the changelog section extractor (``tests/support/release_notes.py``).

``section_body`` slices the Keep-a-Changelog section under a ``## [version]``
heading; the Release workflow pipes its output into the GitHub Release body
(ADR-0023), so a false match or a missed match both corrupt a release.
Order: plain sections → link-heading → prefix safety.
"""

from __future__ import annotations

from support.release_notes import section_body

CHANGELOG = """\
# Changelog

## [0.2.0](https://github.com/robsyc/fastshaql/compare/v0.1.0..v0.2.0) - 2026-08-30

### Features

- New thing

## [0.1.0] - 2026-08-29

First release.
"""


def test_section_body_extracts_last_section_to_end_of_file() -> None:
    body = section_body(CHANGELOG, "0.1.0")
    assert body is not None
    assert "\n".join(body).strip() == "First release."


def test_section_body_matches_heading_with_compare_link() -> None:
    body = section_body(CHANGELOG, "0.2.0")
    assert body is not None
    text = "\n".join(body)
    assert "### Features" in text
    assert "New thing" in text
    assert "First release." not in text


def test_section_body_rejects_prefix_versions() -> None:
    assert section_body(CHANGELOG, "0.1") is None
    assert section_body(CHANGELOG, "0.2") is None
    assert section_body(CHANGELOG, "1.0.0") is None
