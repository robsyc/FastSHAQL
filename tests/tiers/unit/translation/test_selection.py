"""Field-selection translation — ``core/translation/selection.py``.

Unit tier: ``translate_selection`` walking a GraphQL field selection into
SPARQL bind patterns.

Order: selection walk.
"""

from __future__ import annotations

from fastshaql.core.sparql import TriplePattern
from fastshaql.core.translation.selection import (
    iter_field_selections,
    translate_selection,
)
from support.graphql_utils import root_field_node
from support.translation import translation_scope


def test_translate_selection_returns_patterns(relationship_registry) -> None:
    person = relationship_registry.by_type_name["Person"]
    scope = translation_scope(relationship_registry)
    field = root_field_node("{ persons { name } }")
    selection = next(iter_field_selections(field))
    patterns = translate_selection(selection, person, scope)
    assert len(patterns) == 1
    assert isinstance(patterns[0], TriplePattern)
    assert patterns[0].render() == "?iri <http://example.org/name> ?name ."
