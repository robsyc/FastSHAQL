"""SHACL-to-GraphQL bridge with SPARQL translation."""

from importlib.metadata import version

from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser.parse import parse_shapes
from fastshaql.executable import build_executable_schema

__version__ = version("fastshaql")

__all__ = [
    "build_executable_schema",
    "load_shapes",
    "parse_shapes",
]
