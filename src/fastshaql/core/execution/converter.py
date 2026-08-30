"""Convert SPARQL result rows into GraphQL entity dicts.

Groups rows by subject variable, assembles multi-valued list fields,
recursively nests relationship fields via :class:`VariableMap`, and coerces
RDF terms to Python values (ADR-0013, ADR-0014).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rdflib import IdentifiedNode, Literal

from fastshaql.core.ir import NodeShapeIR, ValueType
from fastshaql.core.kernel.constants import IRI_FIELD

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry
    from fastshaql.core.translation import VariableMap

    from .store import SparqlRow, SparqlTerm


def coerce_value(term: SparqlTerm | None) -> object:
    """Coerce a SPARQL binding to a Python value graphql-core can serialize.

    Args:
        term: RDFLib term from a store row, or ``None`` for unbound variables.

    Returns:
        ``str``, ``int``, ``float``, ``bool``, or ``None``.
    """
    match term:
        case None:
            return None
        case Literal():
            return term.toPython()
        case IdentifiedNode():
            return str(term)
        case _:  # pragma: no cover — all SparqlTerm subtypes matched above
            raise TypeError(f"Unsupported SPARQL term type: {type(term)!r}")


def _subject_key(var_map: VariableMap) -> str:
    return str(var_map.subject_var)


def _group_rows_by_var(
    rows: list[SparqlRow],
    var_key: str,
) -> tuple[list[str], dict[str, list[SparqlRow]]]:
    """Group *rows* by coerced binding for *var_key*; preserve first-seen order."""
    order: list[str] = []
    groups: dict[str, list[SparqlRow]] = {}
    for row in rows:
        term = row.get(var_key)
        if term is None:
            continue
        key = str(coerce_value(term))
        if key not in groups:
            order.append(key)
            groups[key] = []
        groups[key].append(row)
    return order, groups


def _init_entity(shape: NodeShapeIR, var_map: VariableMap) -> dict[str, object]:
    entity: dict[str, object] = {}
    for field_name in var_map.fields:
        if field_name == IRI_FIELD:
            continue
        prop = shape.property_shapes.get(field_name)
        if prop is not None and prop.kind.is_list:
            entity[field_name] = list[object]()
    for rel_name in var_map.relationships:
        prop = shape.property_shapes[rel_name]
        if prop.kind.is_list:
            entity[rel_name] = list[object]()
    return entity


def _dedup_list_values(values: list[object]) -> list[object]:
    return list(dict.fromkeys(values))


def _apply_scalar_fields(
    entity: dict[str, object],
    entity_rows: list[SparqlRow],
    shape: NodeShapeIR,
    var_map: VariableMap,
) -> None:
    field_vars = {
        name: (str(var), shape.property_shapes.get(name))
        for name, var in var_map.fields.items()
    }
    for row in entity_rows:
        for field_name, (var_key, prop) in field_vars.items():
            term = row.get(var_key)
            if term is None:
                continue
            is_list = prop is not None and prop.kind.is_list
            if prop is not None and prop.value_type is ValueType.ENUM:
                value = str(term)
            else:
                value = coerce_value(term)
            if is_list:
                cast("list[object]", entity[field_name]).append(value)
            else:
                entity[field_name] = value


def _apply_relationship_fields(
    entity: dict[str, object],
    entity_rows: list[SparqlRow],
    shape: NodeShapeIR,
    var_map: VariableMap,
    registry: ShapeRegistry,
) -> None:
    for rel_name, (child_subject_var, child_map) in var_map.relationships.items():
        prop = shape.property_shapes[rel_name]
        child_shape = registry.resolve_relationship_target(prop, field_name=rel_name)
        child_key = str(child_subject_var)
        child_order, child_groups = _group_rows_by_var(entity_rows, child_key)

        if prop.kind.is_list:
            nested = [
                _build_entity(child_groups[key], child_shape, child_map, registry)
                for key in child_order
            ]
            entity[rel_name] = nested
            continue

        if child_order:
            entity[rel_name] = _build_entity(
                child_groups[child_order[0]],
                child_shape,
                child_map,
                registry,
            )


def _finalize_entity(
    entity: dict[str, object], shape: NodeShapeIR
) -> dict[str, object]:
    for field_name, values in list(entity.items()):
        if isinstance(values, list) and field_name in shape.property_shapes:
            prop = shape.property_shapes[field_name]
            if prop.kind.is_list and prop.value_type is not ValueType.RELATIONSHIP:
                entity[field_name] = _dedup_list_values(cast("list[object]", values))
    return entity


def _build_entity(
    entity_rows: list[SparqlRow],
    shape: NodeShapeIR,
    var_map: VariableMap,
    registry: ShapeRegistry,
) -> dict[str, object]:
    entity = _init_entity(shape, var_map)
    _apply_scalar_fields(entity, entity_rows, shape, var_map)
    _apply_relationship_fields(entity, entity_rows, shape, var_map, registry)
    return _finalize_entity(entity, shape)


def convert_rows(
    rows: list[SparqlRow],
    shape: NodeShapeIR,
    var_map: VariableMap,
    registry: ShapeRegistry,
) -> list[dict[str, object]]:
    """Group rows by subject variable, coerce values, and nest relationships.

    Selection is derived from *var_map* — scalar keys in ``fields``, relationship
    keys in ``relationships``. ``iri`` appears in output only when present in
    ``var_map.fields``.

    Args:
        rows: Store bindings keyed by SPARQL variable name.
        shape: Node shape for datatype lookup and list-field initialization.
        var_map: Variable mapping produced by translation.
        registry: Shape lookup for nested relationship target shapes.

    Returns:
        One dict per entity with coerced scalar, list, and nested values.
    """
    subject_key = _subject_key(var_map)
    order, groups = _group_rows_by_var(rows, subject_key)
    return [_build_entity(groups[key], shape, var_map, registry) for key in order]
