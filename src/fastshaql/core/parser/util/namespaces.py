"""RDF namespace constants for SHACL-family terms.

SHACL 1.2 terms not yet in RDFLib's ``SH`` namespace and Python-keyword
clashes (``sh:class``) are plain ``URIRef`` constants. The ``shnex:``
node-expression vocabulary (absent from RDFLib entirely) ships as a
``Namespace`` so that ``SHNEX["count"]``-style term access works.
"""

from rdflib import Namespace, URIRef

SH_NS = "http://www.w3.org/ns/shacl#"

SH_CLASS = URIRef(f"{SH_NS}class")
SH_CODE_IDENTIFIER = URIRef(f"{SH_NS}codeIdentifier")
SH_IN = URIRef(f"{SH_NS}in")
SH_ROOT_CLASS = URIRef(f"{SH_NS}rootClass")
SH_SHAPE = URIRef(f"{SH_NS}shape")
SH_SHAPE_CLASS = URIRef(f"{SH_NS}ShapeClass")
SH_SPARQL_EXPR = URIRef(f"{SH_NS}sparqlExpr")
SH_TARGET_WHERE = URIRef(f"{SH_NS}targetWhere")
SH_VALUES = URIRef(f"{SH_NS}values")

SHNEX = Namespace("http://www.w3.org/ns/shacl-node-expr#")

__all__ = [
    "SHNEX",
    "SH_CLASS",
    "SH_CODE_IDENTIFIER",
    "SH_IN",
    "SH_NS",
    "SH_ROOT_CLASS",
    "SH_SHAPE",
    "SH_SHAPE_CLASS",
    "SH_SPARQL_EXPR",
    "SH_TARGET_WHERE",
    "SH_VALUES",
]
