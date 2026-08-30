"""VariableAllocator — ``core/translation/variables.py`` (ADR-0013).

Tests verify scoped allocation, deduplication, and stem stacking
through the public ``allocate``, ``push_scope``, and ``pop_scope`` methods.

Order: flat allocation → collision suffixing → scoped prefixing → nested scopes → root/scoped independence.
"""

from __future__ import annotations

from rdflib import Variable

from fastshaql.core.translation.variables import VariableAllocator

# --- Flat allocation ---


def test_variable_allocator_returns_stem_on_first_use() -> None:
    allocator = VariableAllocator()
    assert allocator.allocate("label") == Variable("label")


# --- Collision suffixing ---


def test_variable_allocator_suffixes_on_collision() -> None:
    allocator = VariableAllocator()
    assert allocator.allocate("label") == Variable("label")
    assert allocator.allocate("label") == Variable("label_2")
    assert allocator.allocate("label") == Variable("label_3")


# --- Scoped prefixing ---


def test_variable_allocator_prefixes_stems_in_nested_scope() -> None:
    allocator = VariableAllocator()
    allocator.push_scope("employer")
    assert allocator.allocate("name") == Variable("employer_name")
    allocator.pop_scope()
    assert allocator.allocate("name") == Variable("name")


# --- Nested scopes ---


def test_variable_allocator_joins_nested_scopes_with_underscores() -> None:
    allocator = VariableAllocator()
    allocator.push_scope("knows")
    allocator.push_scope("knows")
    assert allocator.allocate("iri") == Variable("knows_knows_iri")


# --- Root/scoped independence ---


def test_variable_allocator_scoped_stem_distinct_from_root_collision() -> None:
    allocator = VariableAllocator()
    assert allocator.allocate("name") == Variable("name")
    allocator.push_scope("employer")
    assert allocator.allocate("name") == Variable("employer_name")
