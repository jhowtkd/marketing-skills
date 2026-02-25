from __future__ import annotations

import argparse
from typing import Sequence

import uvicorn

from vm_webapp.event_worker import run_worker_loop
from vm_webapp.settings import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m vm_webapp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the VM Web App server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8766)

    worker = subparsers.add_parser("worker", help="Run background event worker")
    worker.add_argument("--poll-interval-ms", type=int, default=500)
    return parser


def run_worker(*, poll_interval_ms: int) -> int:
    settings = Settings()
    run_worker_loop(settings=settings, poll_interval_ms=poll_interval_ms)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "serve":
        uvicorn.run("vm_webapp.app:create_app", factory=True, host=args.host, port=args.port)
        return 0
    if args.command == "worker":
        return run_worker(poll_interval_ms=args.poll_interval_ms)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
