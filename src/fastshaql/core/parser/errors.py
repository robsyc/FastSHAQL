"""Errors raised by SHACL shape parsing.

The unsupported-construct error lives at parser level (not inside
``node_expr/``) so parser utilities — e.g. the strict list walk in
``util/graph_reads.py`` — can raise it without a package import cycle;
``node_expr/shacl_prefixes.py`` likewise imports it to break its cycle with
``node_expr/parse.py``.
"""


class UnsupportedShapeError(ValueError):
    """Raised when a shape construct cannot be mapped to supported IR.

    The parser-wide loud-rejection error — unsupported node expressions,
    target declarations, filter-shape constraints, malformed SHACL lists,
    derived-field boundary violations (ADR-0015/0016).
    """
