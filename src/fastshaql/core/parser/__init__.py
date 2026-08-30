"""SHACL shapes graph → ShapeRegistry.

See: https://www.w3.org/TR/shacl12-core/#shapes
"""

from .parse import parse_shapes

__all__ = ["parse_shapes"]
