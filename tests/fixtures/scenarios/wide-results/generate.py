#!/usr/bin/env python3
"""Generate ``data.ttl`` for the wide-results scenario.

Default parameters are derived from the committed correctness anchor
(``smoke/expected.json``). Larger scales are for manual perf runs against a real
triple store — the evaluation harness generates data in-memory via
``WIDE_RESULTS.data_at`` instead.

Run from repo root::

    uv run python tests/fixtures/scenarios/wide-results/generate.py
    uv run python tests/fixtures/scenarios/wide-results/generate.py --entities 500 --parts 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    if str(TESTS_ROOT) not in sys.path:
        sys.path.insert(0, str(TESTS_ROOT))

    from support.scenarios import WIDE_RESULTS, Scale

    parser = argparse.ArgumentParser(description="Generate wide-results scenario data")
    parser.add_argument(
        "--entities",
        type=int,
        default=WIDE_RESULTS.anchor_scale.params["entities"],
        help="Number of Row entities",
    )
    parser.add_argument(
        "--parts",
        type=int,
        default=WIDE_RESULTS.anchor_scale.params["parts"],
        help="Part entities per row",
    )
    parser.add_argument("--seed", type=int, default=0, help="IRI minting seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=WIDE_RESULTS.root / "data.ttl",
        help="Output Turtle path",
    )
    args = parser.parse_args()
    if args.entities < 1:
        parser.error("--entities must be >= 1")
    if args.parts < 1:
        parser.error("--parts must be >= 1")

    scale = Scale(
        {
            **WIDE_RESULTS.anchor_scale.params,
            "entities": args.entities,
            "parts": args.parts,
            "seed": args.seed,
        },
        f"cli-N{args.entities}-P{args.parts}",
    )
    args.output.write_text(WIDE_RESULTS.generator(scale), encoding="utf-8")
    print(
        f"Wrote {args.output} "
        f"(entities={args.entities}, parts={args.parts}, "
        f"~{args.parts * 2} rows/entity)"
    )


if __name__ == "__main__":
    main()
