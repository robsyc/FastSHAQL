#!/usr/bin/env python3
"""Generate ``data.ttl`` for the deep-nesting scenario.

Default parameters are derived from the committed correctness anchor
(``smoke/expected.json``). Larger scales are for manual perf runs against a real
triple store — the evaluation harness generates data in-memory via
``DEEP_NESTING.data_at`` instead.

Run from repo root::

    uv run python tests/fixtures/scenarios/deep-nesting/generate.py
    uv run python tests/fixtures/scenarios/deep-nesting/generate.py --entities 100 --depth 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    if str(TESTS_ROOT) not in sys.path:
        sys.path.insert(0, str(TESTS_ROOT))

    from support.scenarios import DEEP_NESTING, Scale

    parser = argparse.ArgumentParser(description="Generate deep-nesting scenario data")
    parser.add_argument(
        "--entities",
        type=int,
        default=DEEP_NESTING.anchor_scale.params["entities"],
        help="Number of chains (one root node each)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=DEEP_NESTING.anchor_scale.params["depth"],
        help="Chain depth (child hops per root; depth+1 nodes per chain)",
    )
    parser.add_argument("--seed", type=int, default=0, help="IRI minting seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEEP_NESTING.root / "data.ttl",
        help="Output Turtle path",
    )
    args = parser.parse_args()
    if args.entities < 1:
        parser.error("--entities must be >= 1")
    if args.depth < 1:
        parser.error("--depth must be >= 1")

    scale = Scale(
        {
            **DEEP_NESTING.anchor_scale.params,
            "entities": args.entities,
            "depth": args.depth,
            "seed": args.seed,
        },
        f"cli-d{args.depth}-e{args.entities}",
    )
    args.output.write_text(DEEP_NESTING.generator(scale), encoding="utf-8")
    nodes_per_entity = args.depth + 1
    print(
        f"Wrote {args.output} "
        f"(entities={args.entities}, depth={args.depth}, "
        f"~{nodes_per_entity} nodes/entity)"
    )


if __name__ == "__main__":
    main()
