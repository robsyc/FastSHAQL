"""Union row conversion — ``core/execution/converter.py``'s polymorphic
children (ADR-0026).

An overlap child (rows in both lanes) stamps the first declared member
regardless of row order; the other lane's fields never enter the entity
dict. A child whose discriminator never bound is dropped; a single-valued
union yields the entity or ``None`` — never a list.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

import pytest
from rdflib import Literal, URIRef, Variable

from fastshaql.core.execution.converter import convert_rows
from fastshaql.core.translation.variables import (
    MemberBinding,
    RelationshipBinding,
    VariableMap,
)
from support.builders import EX, shape_with
from support.cases import registry_for

if TYPE_CHECKING:
    from fastshaql.core.execution.store import SparqlRow
    from fastshaql.core.registry import ShapeRegistry

_PARAGRAPH_ROW: SparqlRow = {
    "iri": EX + "article",
    "block_iri": URIRef(EX + "both-1"),
    "block_member": EX + "Paragraph",
    "block_1_text": Literal("Dual-typed"),
}
_IMAGE_ROW: SparqlRow = {
    "iri": EX + "article",
    "block_iri": URIRef(EX + "both-1"),
    "block_member": EX + "Image",
    "block_2_url": Literal("https://example.org/both.png"),
}


def _block_var_map() -> VariableMap:
    """A ``block`` binding over the fixture's two members, fields allocated
    in lane order (``?block_1_text`` / ``?block_2_url``)."""
    return VariableMap(
        subject_var=Variable("iri"),
        fields={},
        relationships={
            "block": RelationshipBinding(
                subject_var=Variable("block_iri"),
                discriminator=Variable("block_member"),
                members=(
                    MemberBinding(
                        EX + "Paragraph",
                        VariableMap(
                            subject_var=Variable("block_iri"),
                            fields={"text": Variable("block_1_text")},
                            relationships={},
                        ),
                    ),
                    MemberBinding(
                        EX + "Image",
                        VariableMap(
                            subject_var=Variable("block_iri"),
                            fields={"url": Variable("block_2_url")},
                            relationships={},
                        ),
                    ),
                ),
            )
        },
    )


@pytest.fixture(scope="module")
def registry() -> ShapeRegistry:
    return registry_for("polymorphic_relationships")


@pytest.mark.parametrize(
    "rows",
    [[_PARAGRAPH_ROW, _IMAGE_ROW], [_IMAGE_ROW, _PARAGRAPH_ROW]],
    ids=["paragraph_first", "image_first"],
)
def test_overlap_child_stamps_first_declared_member(
    registry: ShapeRegistry, rows: list[SparqlRow]
) -> None:
    """Declared-member priority, not first-row-wins: the overlap child
    stamps Paragraph whichever lane's row leads the group, and the Image
    lane's fields never enter the entity dict."""
    (entity,) = convert_rows(
        rows, registry.by_type_name["Article"], _block_var_map(), registry
    )
    assert entity["block"] == [{"__typename": "Paragraph", "text": "Dual-typed"}]


def test_converter_drops_non_member_children(registry: ShapeRegistry) -> None:
    """A child whose discriminator never bound (no lane matched) is dropped
    — the membership constraint reading (ADR-0026)."""
    rows: list[SparqlRow] = [
        {
            "iri": EX + "article",
            "block_iri": URIRef(EX + "none-1"),
        }
    ]
    (entity,) = convert_rows(
        rows, registry.by_type_name["Article"], _block_var_map(), registry
    )
    assert entity["block"] == []


def test_converter_single_valued_union_returns_entity_or_none(
    registry: ShapeRegistry,
) -> None:
    """A single-valued polymorphic field (maxCount 1) yields the entity or
    ``None`` — never a list."""
    article = registry.by_type_name["Article"]
    single = dataclasses.replace(article.property_shapes["block"], max_count=1)
    shape = shape_with(article, block=single)
    rows: list[SparqlRow] = [
        {
            "iri": EX + "article",
            "block_iri": URIRef(EX + "para-1"),
            "block_member": EX + "Paragraph",
            "block_1_text": Literal("Intro"),
        }
    ]
    (entity,) = convert_rows(rows, shape, _block_var_map(), registry)
    assert entity["block"] == {"__typename": "Paragraph", "text": "Intro"}
    (empty,) = convert_rows(
        [{"iri": EX + "article"}], shape, _block_var_map(), registry
    )
    assert empty["block"] is None
