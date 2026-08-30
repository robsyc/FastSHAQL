"""Boundary test — Core framework- and transport-neutrality (ADR-0001/0018).

Statically asserts that no module under ``fastshaql.core`` imports the adapter
package, either framework dependency, or the HTTP transport. A stray
``import fastapi``/``import httpx`` inside Core would otherwise import happily
in CI (the extras are always installed), so the core/adapter split and the
transport-free-core rule (ADR-0018) are enforced here by source analysis, not
by environment isolation. The httpx store itself ships in
``fastshaql.stores.http`` behind the ``httpx`` extra.
"""

from __future__ import annotations

import ast
from pathlib import Path

import fastshaql.core

_FORBIDDEN_TOP_LEVELS = {"fastapi", "django", "httpx"}
_FORBIDDEN_PREFIX = "fastshaql.adapters"


def _imported_modules(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.append(node.module)
    return names


def test_core_imports_no_adapters_frameworks_or_transports() -> None:
    root = Path(fastshaql.core.__file__).parent
    leaks: list[str] = []
    for source in sorted(root.rglob("*.py")):
        tree = ast.parse(source.read_text(), filename=str(source))
        for name in _imported_modules(tree):
            top = name.split(".")[0]
            if top in _FORBIDDEN_TOP_LEVELS or name.startswith(_FORBIDDEN_PREFIX):
                leaks.append(f"{source.relative_to(root)}: {name}")
    assert not leaks, (
        "Core imports a framework, the adapter package, or a transport:\n"
        + "\n".join(leaks)
    )
