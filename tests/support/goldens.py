"""Golden-file comparison helpers.

``canonicalize`` normalises JSON values so list order is insignificant: the
response is documented as ``[Type!]!`` (an unordered list) — RDF multi-valued
properties have no inherent order and the outer query carries no ``ORDER BY``
(see ADR-0010). Lists compare as multisets; dicts stay key-equal; scalars
compare directly.
"""

from __future__ import annotations

import json


def canonicalize(value: object) -> object:
    """Recursively normalise JSON values so list order is insignificant."""
    if isinstance(value, list):
        items = [canonicalize(v) for v in value]
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True))
    if isinstance(value, dict):
        return {k: canonicalize(v) for k, v in value.items()}
    return value
