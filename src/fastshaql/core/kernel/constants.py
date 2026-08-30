"""Shared constants for the fastshaql core pipeline."""

from rdflib import RDF, XSD, URIRef

IRI_FIELD: str = "iri"
"""GraphQL field name for the RDF resource IRI on every object type."""

INLINE_SHAPE_PREFIX: str = "urn:fastshaql:inline:"
"""URN prefix for synthesized blank-node Property IRIs."""

SYNTHETIC_SHAPE_PREFIX: str = "urn:fastshaql:synthetic:"
"""URN prefix for synthetic shapes created for untargeted ``sh:class`` values."""

DIR_LANG_STRING: URIRef = URIRef(
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#dirLangString"
)
"""RDF 1.2 directional language-tagged string datatype (not in rdflib's RDF namespace)."""

LANGUAGE_DATATYPES: frozenset[URIRef] = frozenset({RDF.langString, DIR_LANG_STRING})
"""The language-tagged string types (RDF 1.2 Concepts §3.4) — the language
lane of the string family."""

STRING_FAMILY_DATATYPES: frozenset[URIRef] = LANGUAGE_DATATYPES | {XSD.string}
"""The recognized datatype universe for multi-entry ``sh:datatype`` sets
(SHACL Core §7.1.2) — plain strings plus the language lane."""
