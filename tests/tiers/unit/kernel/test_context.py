"""Accept-Language resolution — ``lang_tags_from_accept_language`` in
``core/kernel/context.py``.

Unit tier: the RFC 9110 §12.5.4 / RFC 4647 basic-range contract — weighting,
dropping, ordering, dedup, sentinels, and the no-normalization-beyond-
lowercasing rule.

Order: worked-example table → weights → ordering/dedup → sentinels → blank/malformed headers.
"""

from __future__ import annotations

import pytest

from fastshaql.core.kernel.context import lang_tags_from_accept_language


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("en", ("en",)),
        ("en;q=0.8, fr;q=0.9", ("fr", "en")),
        ("en-US, en;q=0.8, *;q=0.1", ("en-us", "en", "*")),
        ("de;q=0", ()),
        ("fr, en;q=0.9, fr;q=0.4", ("fr", "en")),
        (None, ()),
        ("", ()),
        ("   ", ()),
    ],
    ids=[
        "single_tag",
        "weight_ordering",
        "subtag_case_and_star",
        "only_q_zero",
        "duplicate_keeps_higher",
        "none_header",
        "empty_header",
        "whitespace_header",
    ],
)
def test_accept_language_table(header: str | None, expected: tuple[str, ...]) -> None:
    assert lang_tags_from_accept_language(header) == expected


# --- Weights ---


@pytest.mark.parametrize(
    "header",
    ["en;q=2", "en;q=1.0000", "en;q=-0.5", "en;q=", "en;q=.5"],
    ids=["above_one", "four_decimals", "negative", "empty_value", "leading_dot"],
)
def test_malformed_weights_default_to_one(header: str) -> None:
    """Out-of-range and malformed weights are ignored — the entry survives
    at the default weight, ordered above a genuine ``q=0.9``."""
    assert lang_tags_from_accept_language(f"{header}, fr;q=0.9") == ("en", "fr")


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("en;q=2;q=0.5, fr;q=0.9", ("fr", "en")),
        ("en;q=00.5, fr;q=0.9", ("en", "fr")),
    ],
    ids=["out_of_range_q_yields_to_later_valid", "leading_zero_q_is_malformed"],
)
def test_invalid_weights_skip_to_next_parameter(
    header: str, expected: tuple[str, ...]
) -> None:
    """Every flavor of invalid ``q`` — malformed, out-of-range, leading
    zeros — is skipped uniformly: a later valid parameter in the same entry
    wins when present, else the weight defaults to 1.0 (``en`` at 1.0
    outranks ``fr`` at 0.9)."""
    assert lang_tags_from_accept_language(header) == expected


def test_three_decimal_weights_parse() -> None:
    assert lang_tags_from_accept_language("en;q=0.123, fr;q=0.12") == ("en", "fr")


def test_weight_surrounded_by_whitespace() -> None:
    assert lang_tags_from_accept_language("en ; q=0.5 , fr") == ("fr", "en")


def test_weight_parameter_name_is_case_insensitive() -> None:
    """RFC 9110 §5.6.6: parameter names are case-insensitive — ``Q=`` is a
    genuine weight, not an unknown parameter (dropping it would flip the
    order by promoting the entry to the default weight)."""
    assert lang_tags_from_accept_language("en;Q=0.5, fr") == ("fr", "en")


def test_uppercase_q_zero_drops_entry() -> None:
    assert lang_tags_from_accept_language("de;Q=0, fr") == ("fr",)


def test_non_q_parameters_are_ignored() -> None:
    assert lang_tags_from_accept_language("en; level=1; q=0.5, fr") == ("fr", "en")


def test_q_zero_zero_zero_drops_entry() -> None:
    assert lang_tags_from_accept_language("de;q=0.000") == ()


# --- Ordering and dedup ---


def test_equal_weights_keep_first_seen_order() -> None:
    assert lang_tags_from_accept_language("nl;q=0.5, de;q=0.5, fr;q=0.5") == (
        "nl",
        "de",
        "fr",
    )


def test_duplicate_tag_replaced_by_higher_weight_occurrence() -> None:
    assert lang_tags_from_accept_language("fr;q=0.4, en;q=0.9, fr;q=0.95") == (
        "fr",
        "en",
    )


def test_duplicate_equal_weights_keep_first_seen() -> None:
    assert lang_tags_from_accept_language("en;q=0.5, fr;q=0.5, en;q=0.5") == (
        "en",
        "fr",
    )


def test_tags_lowercase() -> None:
    assert lang_tags_from_accept_language("EN-gb, FR;q=0.9") == ("en-gb", "fr")


def test_no_subtag_expansion() -> None:
    """``en`` never gains ``en-US`` — range matching in ``langMatches``
    already subsumes it."""
    assert lang_tags_from_accept_language("en") == ("en",)


# --- Sentinels ---


def test_only_star_passes_through() -> None:
    assert lang_tags_from_accept_language("*") == ("*",)


def test_repeated_star_keeps_highest_weighted() -> None:
    """The kept ``*`` occurrence is its highest-weighted one — positioned by
    that weight (0.5 outranks ``en``'s 0.3)."""
    assert lang_tags_from_accept_language("*;q=0.1, en;q=0.3, *;q=0.5") == (
        "*",
        "en",
    )


def test_untagged_sentinel_never_synthesized() -> None:
    assert "" not in lang_tags_from_accept_language("en, *;q=0.1")


# --- Blank and malformed headers ---


@pytest.mark.parametrize(
    "header", [",,", "; q=0.5", " , "], ids=["commas_only", "tagless_entry", "spaces"]
)
def test_malformed_header_yields_empty_chain(header: str) -> None:
    assert lang_tags_from_accept_language(header) == ()
