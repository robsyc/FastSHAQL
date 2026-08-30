"""Quickstart smoke test — parse, build, and run every guided-tour query.

One code path, two entry points::

    just smoke                                        # workspace
    uv run --isolated --no-project --with dist/*.whl demo/smoke.py  # release

Imports core fastshaql only (no adapter or framework dependencies), so the
release workflow can run it unchanged against a built wheel: the quickstart
fixture ships in the repository, not the wheel.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from graphql import GraphQLSchema, graphql

from fastshaql import build_executable_schema, load_shapes, parse_shapes
from fastshaql.core import (
    InMemoryStore,
    QueryContext,
    ResolverContext,
    SparqlStore,
    lang_tags_from_accept_language,
)

QUICKSTART = Path(__file__).resolve().parent / "quickstart"
CATALOG = "http://example.org/graphs/catalog"
LOANS = "http://example.org/graphs/loans"

Check = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class Stop:
    """One tour stop: its query file, request context, and spot checks."""

    name: str
    query_context: QueryContext | None = None
    checks: tuple[Check, ...] = ()


def _genetics_walks_up(data: dict[str, Any]) -> None:
    genetics = next(t for t in data["topics"] if t["prefLabel"] == "Genetics")
    labels = [t["prefLabel"] for t in genetics["broaderTopics"]]
    assert labels == ["Biology", "Science"], labels


def _availability_is_derived(data: dict[str, Any]) -> None:
    works = data["works"]
    states = {w["availability"] for w in works}
    assert states <= {"AVAILABLE", "BORROWED"}, states
    assert "BORROWED" in states, "expected at least one borrowed work"
    fines = [loan["fine"] for loan in data["loans"]]
    assert fines, "expected loans in the default (union) dataset"
    assert min(fines) == 0, fines  # sh:defaultValue fills the fine-less loans
    assert any(fine > 0 for fine in fines), fines  # one closed loan carries a real fine


def _recommendations_exist(data: dict[str, Any]) -> None:
    jane = next(m for m in data["members"] if m["displayName"] == "Jane Doe")
    assert jane["recommendedWorks"], "expected recommendations for Jane"


def _fiction_is_a_subset_of_works(data: dict[str, Any]) -> None:
    assert len(data["works"]) == 10, len(data["works"])
    assert len(data["fictionworks"]) == 5, len(data["fictionworks"])


def _counts(works: int, loans: int) -> Check:
    def check(data: dict[str, Any]) -> None:
        assert len(data["works"]) == works, data["works"]
        assert len(data["loans"]) == loans, data["loans"]

    return check


def _strict_chain_drops_atlas(data: dict[str, Any]) -> None:
    """A strict ``("nl",)`` chain on a required langString title drops the
    English-only Atlas entirely (the S2 ``BOUND`` guard)."""
    titles = {w["title"] for w in data["works"]}
    atlas = "National Geographic Atlas of the World"
    assert atlas not in titles, titles


def _chain_falls_back_to_english_for_atlas(data: dict[str, Any]) -> None:
    """Under the header-derived chain ``("nl", "en")``: Dutch titles win
    where they exist, and the English-only Atlas reappears via fallback
    (under a strict ``("nl",)`` chain it drops out entirely)."""
    titles = {w["title"] for w in data["works"]}
    atlas = "National Geographic Atlas of the World"
    assert atlas in titles, titles


def _union_subtitle_resolves(data: dict[str, Any]) -> None:
    """The string-union subtitle: the tagged lane wins for 1984, Nausicaä's
    plain value resolves via the union's built-in untagged last resort."""
    subtitles = {w["title"]: w["subtitle"] for w in data["works"]}
    assert subtitles["1984"] == "Een klassieke dystopie", subtitles["1984"]
    assert subtitles["Nausicaä van het dal der winden"] == "The full series"


TOUR: tuple[Stop, ...] = (
    Stop("01-first-query"),
    Stop("02-nesting"),
    Stop(
        "03-language",
        QueryContext(lang_tags=("nl",)),
        checks=(_strict_chain_drops_atlas, _union_subtitle_resolves),
    ),
    Stop(
        "03-language",
        QueryContext(lang_tags=lang_tags_from_accept_language("nl, en;q=0.8, *;q=0.1")),
        checks=(_chain_falls_back_to_english_for_atlas, _union_subtitle_resolves),
    ),
    Stop("04-enums-and-scalar-filters"),
    Stop("05-logic"),
    Stop("06-relationship-filters"),
    Stop("07-pagination"),
    Stop("08-inheritance-and-override"),
    Stop("09-recursion"),
    Stop("10-transitive-paths", checks=(_genetics_walks_up,)),
    Stop("11-derived-values", checks=(_availability_is_derived,)),
    Stop(
        "12-derived-relationships",
        QueryContext(lang_tags=("en",)),
        checks=(_recommendations_exist,),
    ),
    Stop("13-derived-targets", checks=(_fiction_is_a_subset_of_works,)),
    Stop("14-named-graphs", checks=(_counts(works=10, loans=6),)),
    Stop(
        "14-named-graphs",
        QueryContext(read_graphs=(CATALOG,)),
        checks=(_counts(works=8, loans=0),),
    ),
    Stop(
        "14-named-graphs",
        QueryContext(read_graphs=(CATALOG, LOANS)),
        checks=(_counts(works=8, loans=6),),
    ),
)


def build_store() -> SparqlStore:
    """Load the quickstart TriG into an in-memory store (union default)."""
    from rdflib import Dataset

    dataset = Dataset(default_union=True)
    dataset.parse(QUICKSTART / "data.trig")
    return InMemoryStore(dataset)


async def run_tour() -> None:
    """Execute every tour stop; assert non-empty results and spot checks."""
    shapes = load_shapes(QUICKSTART / "shapes.ttl")
    schema = build_executable_schema(parse_shapes(shapes))
    store = build_store()

    for stop in TOUR:
        query = (QUICKSTART / "queries" / f"{stop.name}.graphql").read_text()
        result = await graphql(
            schema,
            query,
            context_value=ResolverContext(
                store=store, query_context=stop.query_context
            ),
        )
        assert result.errors is None, (
            f"{stop.name}: {[e.message for e in result.errors]}"
        )
        assert isinstance(result.data, dict), stop.name
        assert result.data, stop.name
        for check in stop.checks:
            check(result.data)
        print(
            f"ok {stop.name}"
            + (f" [{stop.query_context}]" if stop.query_context else "")
        )

    _assert_exclusions(schema)


def _assert_exclusions(schema: GraphQLSchema) -> None:
    """Deactivated properties and private shapes leave no schema trace."""
    from graphql import print_schema

    sdl = print_schema(schema)
    assert "internalNotes" not in sdl, "deactivated property leaked into the schema"
    assert "auditEntries" not in sdl, "private shape leaked into the schema"


def main() -> None:
    asyncio.run(run_tour())
    print("quickstart smoke passed")


if __name__ == "__main__":
    main()
