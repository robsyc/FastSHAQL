"""Variable naming for FILTER EXISTS internal scopes.

``_rf_`` abbreviates **relationship-filter** — variables allocated inside
``FILTER EXISTS`` blocks for relationship filter conditions. They are
namespaced separately from selection-walk variables (see ADR-0009).
"""

from __future__ import annotations


def rf_var_name(prefix: str, field_name: str) -> str:
    """Return a relationship-filter variable name inside an EXISTS block."""
    if prefix:
        return f"_rf_{prefix}_{field_name}"
    return f"_rf_{field_name}"  # pragma: no cover — rf_prefix invariant: always seeded and grown non-empty


def exists_join_var_name(prefix: str, field_name: str) -> str:
    """Return the join subject variable for a nested relationship in EXISTS."""
    if prefix:
        return f"{prefix}_{field_name}_iri"
    return f"{field_name}_iri"  # pragma: no cover — rf_prefix invariant: always seeded and grown non-empty
