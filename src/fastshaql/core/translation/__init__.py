"""GraphQL AST → SPARQL GraphPattern translation.

See ADR-0013 for architecture and :func:`translate_query` for the entry point.
"""

from .query import translate_query
from .variables import VariableMap

__all__ = ["VariableMap", "translate_query"]
