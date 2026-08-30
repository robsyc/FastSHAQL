"""fastshaql async-concurrency load test — drives the example app in-process.

Exercises the async execution spine (ADR-0018): concurrency should beat serial
because the spine overlaps ``await store.query`` across in-flight requests. This
is a local dev perf-smoke tool, not a CI gate; store-backed performance
evaluation lives in ``tests/tiers/evaluation/``.

Run from repo root::

    uv run --package fastshaql-demo python -m demo.throughput \\
        --shapes tests/fixtures/cases/minimal/shapes.ttl \\
        --data tests/fixtures/cases/minimal/data.ttl \\
        --query tests/fixtures/cases/minimal/smoke/query.graphql \\
        --requests 200 --concurrency 20 --latency 0.05
"""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from demo.server import ServerConfig, build_app


def _percentile(sorted_samples: list[float], pct: float) -> float:
    if not sorted_samples:
        return 0.0
    idx = round(pct * (len(sorted_samples) - 1))
    return sorted_samples[min(idx, len(sorted_samples) - 1)]


def _load_query(path_or_inline: str) -> str:
    candidate = Path(path_or_inline)
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8")
    return path_or_inline


async def _run(args: argparse.Namespace) -> None:
    config = ServerConfig(
        shapes=args.shapes,
        data=args.data,
        endpoint=args.endpoint,
        fake_latency=args.latency,
    )
    app = build_app(config)
    payload = {"query": _load_query(args.query)}
    semaphore = asyncio.Semaphore(args.concurrency)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://bench"
    ) as client:
        for _ in range(min(args.concurrency, 5)):
            resp = await client.post("/graphql", json=payload)
            body = resp.json()
            if resp.status_code != 200 or body.get("errors"):
                raise SystemExit(f"warmup failed: HTTP {resp.status_code} {body}")

        async def one_request() -> tuple[float, int]:
            async with semaphore:
                start = time.perf_counter()
                resp = await client.post("/graphql", json=payload)
                return time.perf_counter() - start, resp.status_code

        wall_start = time.perf_counter()
        results = await asyncio.gather(*(one_request() for _ in range(args.requests)))
        wall = time.perf_counter() - wall_start

    samples = sorted(lat for lat, _ in results)
    errors = sum(1 for _, status in results if status != 200)

    backend = config.endpoint or str(config.data)
    print(
        f"shapes={config.shapes} backend={backend} requests={args.requests} "
        f"concurrency={args.concurrency} latency={args.latency}s"
    )
    print(
        f"errors={errors}/{args.requests}  wall={wall:.3f}s  "
        f"throughput={args.requests / wall:.1f} req/s"
    )
    print(
        f"p50={_percentile(samples, 0.50) * 1000:.1f}ms  "
        f"p95={_percentile(samples, 0.95) * 1000:.1f}ms  "
        f"p99={_percentile(samples, 0.99) * 1000:.1f}ms"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="fastshaql async-concurrency load test"
    )
    parser.add_argument(
        "--shapes",
        type=Path,
        required=True,
        help="SHACL shapes file or directory of *.ttl",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
        help="RDF data file or directory (in-memory store)",
    )
    parser.add_argument(
        "--endpoint",
        default=None,
        help="SPARQL query endpoint URL",
    )
    parser.add_argument(
        "--query",
        required=True,
        help="GraphQL query file path or inline query string",
    )
    parser.add_argument("--requests", type=int, default=200, help="Total requests")
    parser.add_argument(
        "--concurrency", type=int, default=20, help="Max in-flight requests"
    )
    parser.add_argument(
        "--latency",
        type=float,
        default=0.0,
        help="Fake per-query store latency (s) — simulates triple-store I/O",
    )
    args = parser.parse_args()
    if args.requests < 1:
        parser.error("--requests must be >= 1")
    if args.concurrency < 1:
        parser.error("--concurrency must be >= 1")
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
