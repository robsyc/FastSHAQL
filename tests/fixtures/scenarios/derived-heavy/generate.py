#!/usr/bin/env python3
"""Generate ``data.ttl`` for the derived-heavy scenario.

Default parameters are derived from the committed correctness anchor
(``smoke/expected.json``). Larger scales are for manual perf runs against a real
triple store — the evaluation harness generates data in-memory via
``DERIVED_HEAVY.data_at`` instead.

Run from repo root::

    uv run python tests/fixtures/scenarios/derived-heavy/generate.py
    uv run python tests/fixtures/scenarios/derived-heavy/generate.py --entities 1000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    if str(TESTS_ROOT) not in sys.path:
        sys.path.insert(0, str(TESTS_ROOT))

    from support.scenarios import DERIVED_HEAVY, Scale

    parser = argparse.ArgumentParser(description="Generate derived-heavy scenario data")
    parser.add_argument(
        "--entities",
        type=int,
        default=DERIVED_HEAVY.anchor_scale.params["entities"],
        help="Number of Thing entities",
    )
    parser.add_argument("--seed", type=int, default=0, help="IRI minting seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=DERIVED_HEAVY.root / "data.ttl",
        help="Output Turtle path",
    )
    args = parser.parse_args()
    if args.entities < 1:
        parser.error("--entities must be >= 1")

    scale = Scale(
        {
            **DERIVED_HEAVY.anchor_scale.params,
            "entities": args.entities,
            "seed": args.seed,
        },
        f"cli-N{args.entities}",
    )
    args.output.write_text(DERIVED_HEAVY.generator(scale), encoding="utf-8")
    print(
        f"Wrote {args.output} "
        f"(entities={args.entities}, 5 derived + 4 asserted fields each)"
    )


if __name__ == "__main__":
    main()
