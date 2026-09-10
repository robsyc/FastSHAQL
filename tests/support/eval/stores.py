"""Store matrix registry — named ``StoreSession`` factories (ADR-0022).

``EVAL_STORE`` (comma-separated store names) selects which legs an evaluation
run exercises; the default is the license-free set. GraphDB Free stays
opt-in: it skips itself out of the matrix when its license file is absent.
One session-scoped container per store.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from support.eval.fuseki import start as start_fuseki
from support.eval.graphdb import start as start_graphdb
from support.eval.oxigraph import start as start_oxigraph
from support.eval.qlever import start as start_qlever

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

    from support.eval.session import StoreSession


@dataclass(frozen=True)
class StoreSpec:
    """One leg of the store matrix: report metadata + the session factory."""

    name: str
    license: str
    """License tier as the report names it: ``oss`` or ``free``."""

    notes: str
    """Store-specific caveats, shown in the report's store table."""

    start: Callable[[], AbstractContextManager[StoreSession]]
    """Context manager: run the container, yield the session, tear down."""


STORES: dict[str, StoreSpec] = {
    "oxigraph": StoreSpec(
        name="oxigraph",
        license="oss",
        notes="standard no-FROM default graph (unnamed-only)",
        start=start_oxigraph,
    ),
    "fuseki": StoreSpec(
        name="fuseki",
        license="oss",
        notes="standard no-FROM default graph (unnamed-only); exact literal fidelity",
        start=start_fuseki,
    ),
    "qlever": StoreSpec(
        name="qlever",
        license="oss",
        notes="union default graph (no knob); load = index rebuild, not live update",
        start=start_qlever,
    ),
    "graphdb": StoreSpec(
        name="graphdb",
        license="free",
        notes=(
            "GraphDB Free — free-to-use proprietary tier, capped at two "
            "concurrent queries / one core / five repositories (a serial "
            "harness never feels the caps)"
        ),
        start=start_graphdb,
    ),
}

DEFAULT_STORES = ("oxigraph", "fuseki", "qlever")


def selected_stores() -> tuple[StoreSpec, ...]:
    """Parse ``EVAL_STORE`` into specs; the default is the license-free set."""
    raw = os.environ.get("EVAL_STORE", ",".join(DEFAULT_STORES))
    # dict.fromkeys: order-preserving dedup — a repeated name would otherwise
    # run (and containerize) the same leg twice.
    names = list(dict.fromkeys(name.strip() for name in raw.split(",") if name.strip()))
    if not names:
        # An explicit-but-empty selection must not collect zero tests and
        # look green — fail the run instead.
        raise SystemExit(
            f"EVAL_STORE={raw!r} selects no stores; unset it for the default "
            f"set ({', '.join(DEFAULT_STORES)}) or name stores explicitly"
        )
    unknown = [name for name in names if name not in STORES]
    if unknown:
        known = ", ".join(sorted(STORES))
        raise SystemExit(
            f"unknown EVAL_STORE entries: {unknown}; known stores: {known}"
        )
    return tuple(STORES[name] for name in names)
