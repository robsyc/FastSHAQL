"""Render RDFLib terms to SPARQL syntax.

Uses RDFLib's ``n3()`` for URIRef, Literal, and BNode rendering.
Variables rendered as ``?name``; ``xsd:boolean`` literals with canonical
lexical form render as the SPARQL ``BooleanLiteral`` (``true``/``false``).

See: https://www.w3.org/TR/sparql12-query/#syntaxTerms
"""

from __future__ import annotations

from rdflib import BNode, Literal, URIRef, Variable
from rdflib.namespace import XSD

type RenderTerm = Variable | URIRef | Literal | BNode
"""Union of RDFLib types that can appear in a SPARQL pattern position."""


def render_term(term: RenderTerm) -> str:
    """Render an RDFLib term to its SPARQL syntax representation."""
    if isinstance(term, Variable):
        return f"?{term}"
    if (
        isinstance(term, Literal)
        and term.datatype == XSD.boolean
        and str(term) in ("true", "false")
    ):
        return str(term)
    return term.n3()
