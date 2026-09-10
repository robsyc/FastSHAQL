"""Shared SPARQL golden strings for filter translation tests."""

from __future__ import annotations

PERSON_NAME_ONLY_SPARQL = """SELECT ?iri ?name
WHERE {
  ?iri a/<http://www.w3.org/2000/01/rdf-schema#subClassOf>* <http://example.org/Person> .
  ?iri <http://example.org/name> ?name .
}"""
