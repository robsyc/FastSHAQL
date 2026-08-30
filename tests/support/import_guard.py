"""Import-guard check: the ``httpx`` extra must fail helpfully without httpx.

Run by the ``import-guard`` just recipe in an isolated uv environment
(``--no-project --with .``): base ``fastshaql`` only — no extras, no dev group —
so httpx is genuinely absent and the wheel layout is what real consumers see.
Stdlib + fastshaql imports only.
"""

from __future__ import annotations

import fastshaql.stores

assert fastshaql.stores.__doc__, "fastshaql.stores must import without any extra"

try:
    from fastshaql.stores.http import HttpxSparqlStore  # noqa: F401
except ImportError as exc:
    message = str(exc)
else:
    raise SystemExit("fastshaql.stores.http imported without httpx — guard is broken")

assert "fastshaql[httpx]" in message, f"guard error lacks the install hint: {message}"
print(f"import guard OK: {message}")
