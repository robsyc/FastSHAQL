"""RDFLib term rendering — ``core/sparql/terms.py``.

Unit tier: ``render_term`` output for variables, IRIs, and the plain,
datatype-tagged, language-tagged, and blank-node literal forms.

Order: variable → URIRef → plain literal → datatype literal → lang literal → blank node.
"""

from __future__ import annotations

import pytest
from rdflib import BNode, Literal, URIRef, Variable
from rdflib.namespace import XSD

from fastshaql.core.sparql.terms import RenderTerm, render_term

EX = URIRef("http://example.org/")


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        pytest.param(Variable("iri"), "?iri", id="variable"),
        pytest.param(EX + "label", "<http://example.org/label>", id="uri-ref"),
        pytest.param(Literal("hello"), '"hello"', id="plain-literal"),
        pytest.param(
            Literal("42", datatype=XSD.integer),
            '"42"^^<http://www.w3.org/2001/XMLSchema#integer>',
            id="datatype-literal",
        ),
        pytest.param(Literal("bonjour", lang="fr"), '"bonjour"@fr', id="lang-literal"),
        pytest.param(BNode("abc"), "_:abc", id="bnode"),
    ],
)
def test_render_term(term: RenderTerm, expected: str) -> None:
    assert render_term(term) == expected
