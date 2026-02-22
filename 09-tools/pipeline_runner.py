#!/usr/bin/env python3
"""Threaded pipeline runner entrypoint (foundation stack)."""

from __future__ import annotations

import argparse
from pathlib import Path

from executor import approve_stage, dump_json, get_status, retry_stage, run_until_gate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("pipeline-runner")
    parser.add_argument(
        "--runtime-root",
        default="runtime",
        help="Runtime state root path",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--project-id", required=True)
    run_parser.add_argument("--thread-id", required=True)
    run_parser.add_argument("--stack-path", required=True)
    run_parser.add_argument("--query", required=True)

    approve_parser = sub.add_parser("approve")
    approve_parser.add_argument("--project-id", required=True)
    approve_parser.add_argument("--thread-id", required=True)
    approve_parser.add_argument("--stage", required=True)

    status_parser = sub.add_parser("status")
    status_parser.add_argument("--project-id", required=True)
    status_parser.add_argument("--thread-id", required=True)

    retry_parser = sub.add_parser("retry")
    retry_parser.add_argument("--project-id", required=True)
    retry_parser.add_argument("--thread-id", required=True)
    retry_parser.add_argument("--stage", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runtime_root = Path(args.runtime_root)

    if args.command == "run":
        result = run_until_gate(
            runtime_root=runtime_root,
            project_id=args.project_id,
            thread_id=args.thread_id,
            stack_path=args.stack_path,
            query=args.query,
        )
        print(dump_json(result))
        return 0

    if args.command == "approve":
        result = approve_stage(
            runtime_root=runtime_root,
            project_id=args.project_id,
            thread_id=args.thread_id,
            stage_id=args.stage,
        )
        print(dump_json(result))
        return 0

    if args.command == "status":
        result = get_status(
            runtime_root=runtime_root,
            project_id=args.project_id,
            thread_id=args.thread_id,
        )
        print(dump_json(result))
        return 0

    if args.command == "retry":
        result = retry_stage(
            runtime_root=runtime_root,
            project_id=args.project_id,
            thread_id=args.thread_id,
            stage_id=args.stage,
        )
        print(dump_json(result))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
