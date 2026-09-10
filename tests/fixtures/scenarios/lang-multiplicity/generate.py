#!/usr/bin/env python3
"""Generate ``data.ttl`` for the lang-multiplicity scenario.

Default parameters are derived from the committed correctness anchor
(``smoke/expected.json``). Larger scales are for manual perf runs against a real
triple store — the evaluation harness generates data in-memory via
``LANG_MULTIPLICITY.data_at`` instead.

Run from repo root::

    uv run python tests/fixtures/scenarios/lang-multiplicity/generate.py
    uv run python tests/fixtures/scenarios/lang-multiplicity/generate.py --entities 1000 --langs 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    if str(TESTS_ROOT) not in sys.path:
        sys.path.insert(0, str(TESTS_ROOT))

    from support.scenarios import LANG_MULTIPLICITY, Scale

    parser = argparse.ArgumentParser(
        description="Generate lang-multiplicity scenario data"
    )
    parser.add_argument(
        "--entities",
        type=int,
        default=LANG_MULTIPLICITY.anchor_scale.params["entities"],
        help="Number of Doc entities",
    )
    parser.add_argument(
        "--langs",
        type=int,
        default=LANG_MULTIPLICITY.anchor_scale.params["langs"],
        help="Distinct title languages per doc (from the fixed tag pool)",
    )
    parser.add_argument("--seed", type=int, default=0, help="IRI minting seed")
    parser.add_argument(
        "--output",
        type=Path,
        default=LANG_MULTIPLICITY.root / "data.ttl",
        help="Output Turtle path",
    )
    args = parser.parse_args()
    if args.entities < 1:
        parser.error("--entities must be >= 1")
    if args.langs < 1 or args.langs > 8:
        parser.error("--langs must be within the 8-tag pool (1..8)")

    scale = Scale(
        {
            **LANG_MULTIPLICITY.anchor_scale.params,
            "entities": args.entities,
            "langs": args.langs,
            "seed": args.seed,
        },
        f"cli-N{args.entities}-L{args.langs}",
    )
    args.output.write_text(LANG_MULTIPLICITY.generator(scale), encoding="utf-8")
    print(
        f"Wrote {args.output} "
        f"(entities={args.entities}, langs={args.langs}, "
        f"~{args.langs} titles/entity)"
    )


if __name__ == "__main__":
    main()
