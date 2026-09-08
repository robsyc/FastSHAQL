"""Translate GraphQL ``where`` arguments into SPARQL filter expressions (ADR-0009).

Two internal modules behind this surface: ``where.py`` (the where-object →
patterns/expression pipeline) and ``exists_scope.py`` (the FilterContext
strategies and the FILTER EXISTS builder); ``operators.py`` and
``literals.py`` carry operator emission and literal coercion.
"""

from .exists_scope import ExistsContext, FilterContext, RootFilterContext
from .where import (
    compute_promoted_fields,
    extract_pagination_arguments,
    extract_where_argument,
    translate_where_filter,
)

__all__ = [
    "ExistsContext",
    "FilterContext",
    "RootFilterContext",
    "compute_promoted_fields",
    "extract_pagination_arguments",
    "extract_where_argument",
    "translate_where_filter",
]
