"""Resolve ``sh:prefixes`` declarations on node expressions (SHACL-SPARQL §2).

See ADR-0015 — direct ``sh:declare`` only; ``owl:imports`` traversal is a
permanent scope exclusion (fastshaql never walks ``owl:imports``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import SH

from ...sparql.lex import EXPAND_TOKEN
from ..errors import UnsupportedShapeError

if TYPE_CHECKING:
    import re

    from rdflib import Graph
    from rdflib.term import Node


def parse_shacl_prefixes(graph: Graph, node: Node) -> dict[str, str]:
    """Return prefix → namespace map from ``sh:prefixes`` on *node*.

    Each ``sh:declare`` value is a prefix declaration carrying exactly one
    ``sh:prefix`` and one ``sh:namespace`` (SHACL-SPARQL §2). They are direct
    property values, not an ``rdf:List``.

    Args:
        graph: SHACL shapes graph.
        node: Node-expression blank node carrying optional ``sh:prefixes``.

    Returns:
        Empty dict when ``sh:prefixes`` is absent.

    Raises:
        UnsupportedShapeError: When the same prefix maps to two different
            namespaces — an ill-formed shapes graph (SHACL-SPARQL §2).
    """
    prefixes_node = graph.value(node, SH.prefixes)
    if prefixes_node is None:
        return {}

    result: dict[str, str] = {}
    for decl in graph.objects(prefixes_node, SH.declare):
        prefix = graph.value(decl, SH.prefix)
        namespace = graph.value(decl, SH.namespace)
        if prefix is None or namespace is None:
            continue
        prefix_str = str(prefix)
        namespace_str = str(namespace)
        if result.get(prefix_str, namespace_str) != namespace_str:
            raise UnsupportedShapeError(
                f"prefix {prefix_str!r} maps to conflicting namespaces "
                f"({result[prefix_str]!r} vs {namespace_str!r}) in sh:prefixes on {node}"
            )
        result[prefix_str] = namespace_str
    return result


def expand_sparql_prefixes(text: str, prefixes: dict[str, str]) -> str:
    """Expand prefixed names in author SPARQL text to full IRIs (ADR-0015).

    String literals (SPARQL 1.2 [176]-[179]), IRIREFs ([159]), and comments
    (§19.4) are protected: prefix-looking spans inside them are left untouched,
    so literal values and absolute IRIs are never corrupted and diagnostics
    rendered from the expanded text stay readable.

    Unknown prefixes are left unchanged. ``$this`` and variables are untouched.

    Args:
        text: Author ``sh:sparqlExpr`` or ``sh:select`` body text.
        prefixes: Resolved ``sh:prefixes`` map from :func:`parse_shacl_prefixes`.

    Returns:
        Text with known ``prefix:local`` occurrences in code position
        replaced by full IRIs ``<namespace+local>``.
    """
    if not prefixes:
        return text

    def _replace(match: re.Match[str]) -> str:
        prefix = match.group("prefix")
        if prefix is None:
            return match.group(0)  # protected region: string, IRIREF, or comment
        namespace = prefixes.get(prefix)
        if namespace is None:
            return match.group(0)
        return f"<{namespace}{match.group('local')}>"

    return EXPAND_TOKEN.sub(_replace, text)
