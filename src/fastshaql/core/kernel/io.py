"""RDF graph loading — upstream of SHACL parsing."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from rdflib import Graph
from rdflib.util import SUFFIX_FORMAT_MAP

type ShapeSource = str | Path | Graph


def load_shapes(
    source: ShapeSource | Sequence[ShapeSource],
    *,
    format: str | None = None,  # noqa: A002 — mirrors rdflib Graph.parse(format=...)
) -> Graph:
    """Load SHACL shape definitions from files, URLs, inline RDF, or graphs.

    Accepts a single source or a sequence of sources to merge into one graph.
    A string is an existing path or URL when it looks like one, else inline
    RDF (default format turtle). A directory contributes its RDF files —
    every file whose suffix rdflib recognizes (see
    ``rdflib.util.SUFFIX_FORMAT_MAP``), non-recursive, sorted, fail-loud when
    empty. Anything more selective (recursion, naming patterns) is a
    ``Path.glob`` call at the caller, whose results merge as ordinary files.

    Args:
        source: Path, URL, inline RDF string, existing graph, directory, or
            a list thereof.
        format: Optional rdflib format override for every parse call.

    Returns:
        An rdflib ``Graph`` containing the merged triples.
    """
    if isinstance(source, Graph):
        return source

    graph = Graph()
    for leaf in _expand_source(source):
        _merge_source(graph, leaf, format=format)
    return graph


def _expand_source(source: ShapeSource | Sequence[ShapeSource]) -> list[ShapeSource]:
    """Normalize *source* into leaf sources, expanding directories."""
    if isinstance(source, Graph):
        return [source]
    if isinstance(source, (str, Path)):
        return _expand_pathlike(source)
    if isinstance(source, Sequence):
        return [leaf for item in source for leaf in _expand_source(item)]
    raise TypeError(
        f"load_shapes expected str, Path, Graph, or sequence thereof; got {type(source)!r}"
    )


def _expand_pathlike(source: str | Path) -> list[ShapeSource]:
    """Expand one path-like source into its leaf sources."""
    path = Path(source)
    if path.is_dir():
        files: list[ShapeSource] = sorted(
            f for f in path.iterdir() if f.suffix.lstrip(".") in SUFFIX_FORMAT_MAP
        )
        if not files:
            raise FileNotFoundError(
                f"no RDF files (rdflib-recognized suffixes) in directory: {path}"
            )
        return files
    return [source]


def _merge_source(
    graph: Graph,
    source: ShapeSource,
    *,
    format: str | None,  # noqa: A002
) -> None:
    """Merge one leaf source (never a directory) into *graph*."""
    if isinstance(source, Graph):
        graph += source
        return

    if (
        isinstance(source, Path)
        or Path(source).exists()
        or source.startswith(("http://", "https://", "file://"))
    ):
        graph.parse(source, format=format)
    else:
        graph.parse(data=source, format=format or "turtle")
