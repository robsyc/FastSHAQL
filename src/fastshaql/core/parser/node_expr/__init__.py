"""Parse ``sh:values`` node expressions into :class:`NodeExprIR` (ADR-0015).

Public surface is :func:`parse_node_expr` / :func:`parse_default_value`
(the ``sh:values`` and ``sh:defaultValue`` host predicates), the semantic checks
(:func:`arm_label`, :func:`reject_derived_path_targets` —
:func:`is_multivalued_capable` lives beside the IR union in
``core/ir/node_expr.py``) and :class:`UnsupportedShapeError` (defined at
parser level, ``core/parser/errors.py``); the
select-body surgery (``select_scan``), prefix resolution
(``shacl_prefixes``) and filter-shape parsing (``filter_shape``) live as
sibling modules behind these re-exports.
"""

from fastshaql.core.ir.node_expr import is_multivalued_capable

from ..errors import UnsupportedShapeError
from .parse import parse_default_value, parse_expr_object, parse_node_expr
from .semantics import arm_label, reject_derived_path_targets

__all__ = [
    "UnsupportedShapeError",
    "arm_label",
    "is_multivalued_capable",
    "parse_default_value",
    "parse_expr_object",
    "parse_node_expr",
    "reject_derived_path_targets",
]
