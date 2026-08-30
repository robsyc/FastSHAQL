"""Package smoke tests — ``fastshaql/``.

Verifies the package imports, exposes its documented public entry points, and
that the runtime ``__version__`` agrees with the installed distribution metadata
(no brittle value pin).

Order: public API surface → version metadata consistency.
"""

from __future__ import annotations

import importlib.metadata

import fastshaql


def test_public_api_is_importable() -> None:
    """The documented public entry points are exposed on the top-level package."""
    from fastshaql import build_executable_schema, load_shapes, parse_shapes

    assert callable(build_executable_schema)
    assert callable(load_shapes)
    assert callable(parse_shapes)


def test_version_matches_distribution_metadata() -> None:
    """The runtime ``__version__`` agrees with the installed distribution metadata."""
    assert fastshaql.__version__ == importlib.metadata.version("fastshaql")
