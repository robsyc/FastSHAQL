#!/usr/bin/env python3
"""Generate ``data.ttl`` for the cartesian scenario.

Default parameters match the committed correctness anchor
(``smoke/expected.json``). Larger scales are for manual perf runs against a real
triple store — the evaluation harness generates data in-memory via
``CARTESIAN.data_at`` instead.

Run from repo root::

    uv run python tests/fixtures/scenarios/cartesian/generate.py
    uv run python tests/fixtures/scenarios/cartesian/generate.py --entities 100 --multi-value 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    if str(TESTS_ROOT) not in sys.path:
        sys.path.insert(0, str(TESTS_ROOT))

    from support.scenarios import CARTESIAN, Scale

    parser = argparse.ArgumentParser(description="Generate cartesian scenario data")
    parser.add_argument(
        "--entities", type=int, default=1, help="Number of Thing entities"
    )
    parser.add_argument(
        "--multi-value", type=int, default=2, help="Values per multi-valued field"
    )
    parser.add_argument("--seed", type=int, default=0, help="IRI minting seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=CARTESIAN.root / "data.ttl",
        help="Output Turtle path",
    )
    args = parser.parse_args()
    if args.entities < 1:
        parser.error("--entities must be >= 1")
    if args.multi_value < 1:
        parser.error("--multi-value must be >= 1")

    scale = Scale(
        {"entities": args.entities, "multi_value": args.multi_value, "seed": args.seed},
        f"cli-N{args.entities}-K{args.multi_value}",
    )
    args.output.write_text(CARTESIAN.generator(scale), encoding="utf-8")
    rows_per_entity = args.multi_value**4
    print(
        f"Wrote {args.output} "
        f"(entities={args.entities}, multi_value={args.multi_value}, "
        f"~{rows_per_entity} rows/entity)"
    )


if __name__ == "__main__":
    main()
