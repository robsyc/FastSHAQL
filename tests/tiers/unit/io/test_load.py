"""Shape source loading and merge — ``core/io.py``.

Unit tier: every accepted source type (``Path``, ``str`` path, inline Turtle,
``rdflib.Graph`` passthrough, directory walk), multi-source list merging,
explicit format override, and fail-loud ``TypeError`` / ``FileNotFoundError``
rejection of bad inputs.

Order: single source → source-type equivalence → directory walk → inline string → Graph passthrough → list merge → format override → type rejection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF

from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser import parse_shapes
from support.cases import CASES_ROOT

if TYPE_CHECKING:
    from pathlib import Path

P = URIRef("http://example.org/p")
V = Literal("x")


def test_load_shapes_single_ttl_file(minimal_registry) -> None:
    graph = load_shapes(CASES_ROOT / "minimal" / "shapes.ttl")
    assert len(graph) > 0
    assert parse_shapes(graph) == minimal_registry


def test_load_shapes_path_and_str_equivalent() -> None:
    path = CASES_ROOT / "minimal" / "shapes.ttl"
    from_path = load_shapes(path)
    from_str = load_shapes(str(path))
    assert isomorphic(from_path, from_str)


def _write_ttl(path: Path, name: str, subject_local: str) -> Path:
    file = path / name
    file.write_text(
        f'@prefix ex: <http://example.org/> .\nex:{subject_local} ex:p "x" .',
        encoding="utf-8",
    )
    return file


def test_load_shapes_directory_walks_rdf_files(tmp_path: Path) -> None:
    """A directory source walks its RDF files — every suffix rdflib
    recognizes (``SUFFIX_FORMAT_MAP``); other files are ignored."""
    _write_ttl(tmp_path, "b.ttl", "b")
    _write_ttl(tmp_path, "a.trig", "a")
    (tmp_path / "notes.txt").write_text("not rdf", encoding="utf-8")

    graph = load_shapes(tmp_path)

    assert len(graph) == 2
    assert (URIRef("http://example.org/a"), P, V) in graph
    assert (URIRef("http://example.org/b"), P, V) in graph


def test_load_shapes_directory_walks_any_rdflib_suffix(tmp_path: Path) -> None:
    """Suffix recognition is rdflib's, not a fastshaql allowlist — e.g. N-Triples."""
    (tmp_path / "a.nt").write_text(
        '<http://example.org/a> <http://example.org/p> "x" .', encoding="utf-8"
    )

    graph = load_shapes(tmp_path)

    assert (URIRef("http://example.org/a"), P, V) in graph


def test_load_shapes_directory_walk_is_non_recursive(tmp_path: Path) -> None:
    """Directory walking stays one level deep; recursion is the caller's
    explicit ``Path.glob``."""
    _write_ttl(tmp_path, "root.ttl", "root")
    nested = tmp_path / "nested"
    nested.mkdir()
    _write_ttl(nested, "deep.ttl", "deep")

    graph = load_shapes(tmp_path)

    assert len(graph) == 1
    assert (URIRef("http://example.org/root"), P, V) in graph


def test_load_shapes_directory_str_path(tmp_path: Path) -> None:
    _write_ttl(tmp_path, "one.ttl", "one")
    from_path = load_shapes(tmp_path)
    from_str = load_shapes(str(tmp_path))
    assert isomorphic(from_path, from_str)


def test_load_shapes_empty_directory_raises(tmp_path: Path) -> None:
    (tmp_path / "unrelated.csv").write_text("not rdf", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="no RDF files"):
        load_shapes(tmp_path)


def test_load_shapes_sequence_items_expand(tmp_path: Path) -> None:
    """Directories expand inside sequences too — flattening, not nesting."""
    _write_ttl(tmp_path, "dir.ttl", "dir")
    inline = '@prefix ex: <http://example.org/> .\nex:inline ex:p "i" .'

    graph = load_shapes([tmp_path, inline])

    assert len(graph) == 2


def test_load_shapes_inline_turtle_string() -> None:
    turtle = (
        "@prefix sh: <http://www.w3.org/ns/shacl#> .\n"
        "@prefix ex: <http://example.org/> .\n"
        'ex:InlineShape a sh:NodeShape ; sh:codeIdentifier "Inline" .'
    )
    graph = load_shapes(turtle)
    inline_shape = URIRef("http://example.org/InlineShape")
    assert (
        inline_shape,
        RDF.type,
        URIRef("http://www.w3.org/ns/shacl#NodeShape"),
    ) in graph


def test_load_shapes_graph_passthrough() -> None:
    original = Graph()
    original.add(
        (
            URIRef("http://ex/s"),
            URIRef("http://ex/p"),
            Literal("v"),
        )
    )
    loaded = load_shapes(original)
    assert loaded is original


def test_load_shapes_merges_list_of_sources() -> None:
    turtle_a = '@prefix ex: <http://example.org/> .\nex:a ex:p "1" .'
    turtle_b = '@prefix ex: <http://example.org/> .\nex:b ex:p "2" .'
    graph = load_shapes([turtle_a, turtle_b])
    assert len(graph) == 2


def test_load_shapes_merges_graph_and_inline() -> None:
    fragment = Graph()
    fragment.add(
        (
            URIRef("http://ex/extra"),
            URIRef("http://ex/p"),
            Literal("x"),
        )
    )
    minimal_path = CASES_ROOT / "minimal" / "shapes.ttl"
    graph = load_shapes([fragment, minimal_path])
    assert len(graph) > len(load_shapes(minimal_path))


def test_load_shapes_empty_list() -> None:
    graph = load_shapes([])
    assert len(graph) == 0


def test_load_shapes_explicit_format_override(tmp_path: Path) -> None:
    content = '@prefix ex: <http://example.org/> .\nex:s ex:p "ok" .'
    path = tmp_path / "shapes.rdf"
    path.write_text(content, encoding="utf-8")
    graph = load_shapes(path, format="turtle")
    subject = URIRef("http://example.org/s")
    assert (subject, URIRef("http://example.org/p"), Literal("ok")) in graph


def test_load_shapes_rejects_invalid_type() -> None:
    with pytest.raises(TypeError):
        load_shapes(cast("Any", object()))


@pytest.mark.parametrize("bad_item", [42, None, 3.14])
def test_load_shapes_rejects_invalid_list_item(bad_item: Any) -> None:
    with pytest.raises(TypeError):
        load_shapes([bad_item])
