"""Parser utilities: identifier derivation, graph reads, namespace constants."""

from .graph_reads import (
    first_localized_str,
    is_deactivated,
    object_int,
    object_str,
    object_uri,
    rdf_list,
    strict_rdf_list,
)
from .identifiers import (
    MissingCompositePathCodeIdentifierError,
    graphql_field_name,
    graphql_type_name,
    property_graphql_field_name,
    safe_python_identifier,
    synthesize_inline_shape_iri,
)
from .namespaces import (
    SH_CLASS,
    SH_CODE_IDENTIFIER,
    SH_IN,
    SH_NS,
    SH_ROOT_CLASS,
    SH_SHAPE,
    SH_SHAPE_CLASS,
    SH_SPARQL_EXPR,
    SH_TARGET_WHERE,
    SH_VALUES,
    SHNEX,
)

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
    "MissingCompositePathCodeIdentifierError",
    "first_localized_str",
    "graphql_field_name",
    "graphql_type_name",
    "is_deactivated",
    "object_int",
    "object_str",
    "object_uri",
    "property_graphql_field_name",
    "rdf_list",
    "safe_python_identifier",
    "strict_rdf_list",
    "synthesize_inline_shape_iri",
]
