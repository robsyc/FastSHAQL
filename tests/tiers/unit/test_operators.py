"""Operator registry ↔ schema filter inputs — ``core/operators.py`` + ``core/schema/filters.py``.

Unit tier: verifies GraphQL operator input types expose exactly the fields
declared in ``OPERATOR_INPUT_SPECS``.

Order: registry parity with ``build_operator_inputs``.
"""

from __future__ import annotations

from fastshaql.core.kernel.operators import (
    OPERATOR_INPUT_SPECS,
    operator_field_names,
)
from fastshaql.core.schema.filters import build_operator_inputs


def test_operator_registry_matches_schema() -> None:
    """GraphQL operator inputs expose exactly the fields declared in the registry."""
    built = build_operator_inputs()
    for name, spec in OPERATOR_INPUT_SPECS.items():
        assert set(built[name].fields) == operator_field_names(spec)
