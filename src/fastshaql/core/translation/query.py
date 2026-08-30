"""Translate GraphQL selection subtrees into SPARQL SELECT queries.

Bridges graphql-core AST (GraphQL spec §5) to the SPARQL composite tree
(SPARQL spec §16). See ADR-0013 for the composite tree architecture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, URIRef, Variable

from fastshaql.core.kernel.constants import IRI_FIELD
from fastshaql.core.sparql import (
    Pattern,
    PredicatePath,
    SelectQuery,
    TriplePattern,
)

from .field_binding import bind_promoted_fields
from .filters import (
    compute_promoted_fields,
    extract_pagination_arguments,
    extract_where_argument,
    translate_where_filter,
)
from .filters.context import RootFilterContext
from .node_expr import translate_node_expr
from .scope import TranslationScope
from .selection import iter_field_selections, translate_selection
from .variables import TranslationResult, VariableAllocator
from .where_assembly import WhereParts, assemble_where

if TYPE_CHECKING:
    from graphql.language.ast import FieldNode

    from fastshaql.core.ir import NodeShapeIR
    from fastshaql.core.kernel.context import QueryContext
    from fastshaql.core.registry import ShapeRegistry


def translate_query(
    shape: NodeShapeIR,
    field_node: FieldNode,
    registry: ShapeRegistry,
    query_context: QueryContext | None = None,
) -> TranslationResult:
    """Translate a root query field selection into a :class:`TranslationResult`.

    Always projects ``?iri`` and emits the target emission: the
    target-class ``rdf:type`` triple, or the ``sh:targetNode`` expression's
    lowering with the shape IRI as focus term (ADR-0016). Delegates per-field
    work to :func:`translate_selection`.

    Args:
        shape: Node shape for the root query field.
        field_node: Parsed GraphQL field AST (selection + ``where``).
        registry: Shape lookup from :func:`~fastshaql.core.parser.parse_shapes`.
        query_context: Optional cross-cutting parameters (language chain,
            read-scope graphs).

    Returns:
        Renderable SPARQL query and variable map for row conversion.

    Raises:
        ValueError: When the shape carries no supported target
            (:func:`_target_entity_patterns` — the single raise site), or when
            ``query_context.write_graph`` is set — the slot is reserved for
            the future writes era and reads never consume it.
    """
    if query_context is not None and query_context.write_graph is not None:
        raise ValueError(
            "QueryContext.write_graph is reserved for the future writes era "
            "(SPARQL Update WITH / Graph Store Protocol target); the "
            "read-only query pipeline never consumes it — leave it unset"
        )
    where_arg = extract_where_argument(field_node)
    promoted = compute_promoted_fields(where_arg, shape)
    limit, offset = extract_pagination_arguments(field_node)
    paginate = limit is not None or offset is not None

    allocator = VariableAllocator()
    subject = allocator.allocate(IRI_FIELD)
    scope = TranslationScope(
        subject=subject,
        allocator=allocator,
        registry=registry,
        lang_tags=query_context.lang_tags if query_context is not None else (),
    )
    entity_patterns = _target_entity_patterns(shape, subject)
    scope.projection.append(subject)

    selected_names: list[str] = []
    selection_patterns: list[Pattern] = []
    for selection in iter_field_selections(field_node):
        selected_names.append(selection.name.value)
        selection_patterns.extend(
            translate_selection(selection, shape, scope, promoted)
        )
    selected = frozenset(selected_names)

    promoted_patterns = bind_promoted_fields(shape, scope, promoted, selected)
    filter_ctx = RootFilterContext.from_scope(
        scope, isolated=paginate, selected=selected
    )
    filter_patterns = translate_where_filter(where_arg, filter_ctx, shape, registry)

    where = assemble_where(
        WhereParts(
            entity=tuple(entity_patterns),
            selection=tuple(selection_patterns),
            promoted=tuple(promoted_patterns),
            filters=tuple(filter_patterns),
        ),
        subject=subject,
        paginate=paginate,
        limit=limit,
        offset=offset,
    )
    query = SelectQuery(
        projection=tuple(scope.projection),
        where=where,
        from_default=tuple(URIRef(g) for g in query_context.read_graphs)
        if query_context is not None
        else (),
    )
    return TranslationResult(query=query, var_map=scope.var_map())


def _target_entity_patterns(shape: NodeShapeIR, subject: Variable) -> list[Pattern]:
    """Root-entity emission for the shape's target (ADR-0016): the
    target-class ``rdf:type`` triple, or the target expression's lowering
    with the shape IRI as focus term — pagination and filters join on
    ``?iri`` either way."""
    if shape.target_class is not None:
        return [
            TriplePattern(
                subject=subject,
                predicate=PredicatePath(RDF.type),
                object=shape.target_class,
            )
        ]
    if shape.target_expr is not None:
        return translate_node_expr(
            shape.target_expr, focus_term=shape.iri, value_var=subject
        )
    raise ValueError(
        f"Shape {shape.graphql_type_name!r} has no supported target — "
        "cannot translate root query field"
    )
