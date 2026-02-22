#!/usr/bin/env python3
"""Run structural and language quality gates for a compound-growth workspace."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED_FILES = [
    "research/market-landscape.md",
    "research/competitor-gaps.md",
    "research/customer-language.md",
    "research/pricing-packaging.md",
    "strategy/voice-profile.md",
    "strategy/positioning-angles.md",
    "strategy/chosen-angle.md",
    "strategy/keyword-opportunities.md",
    "strategy/content-structure.md",
    "strategy/quick-wins-90d.md",
    "assets/landing-page-copy.md",
    "assets/email-sequence.md",
    "assets/lead-magnet.md",
    "assets/distribution-plan.md",
    "review/expert-synthesis.md",
    "review/rejection-notes.md",
    "review/next-iteration-plan.md",
]

RESEARCH_FILES = [
    "research/market-landscape.md",
    "research/competitor-gaps.md",
    "research/customer-language.md",
    "research/pricing-packaging.md",
]

BUZZWORDS = [
    "revolutionary",
    "game-changing",
    "unlock your potential",
    "cutting-edge",
    "synergy",
    "delve",
    "harness the power",
    "in today's fast-paced",
    "revolucionário",
    "inovador",
    "incrível transformação",
    "potencialize",
    "sinergia",
    "desbloqueie seu potencial",
    "no cenário atual",
]

SOURCE_PATTERNS = [
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\[source:?", re.IGNORECASE),
    re.compile(r"fonte:?", re.IGNORECASE),
]


class GateResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)



def check_required_files(workspace: Path, result: GateResult) -> None:
    for rel in REQUIRED_FILES:
        if not (workspace / rel).exists():
            result.add_error(f"Missing required file: {rel}")



def check_research_sources(workspace: Path, result: GateResult) -> None:
    for rel in RESEARCH_FILES:
        path = workspace / rel
        if not path.exists():
            continue
        content = path.read_text()
        has_source = any(pattern.search(content) for pattern in SOURCE_PATTERNS)
        if not has_source:
            result.add_warning(f"No explicit source marker found in: {rel}")



def check_buzzwords(workspace: Path, result: GateResult) -> None:
    targets = [workspace / "assets", workspace / "strategy"]
    for target in targets:
        if not target.exists():
            continue
        for md_file in target.rglob("*.md"):
            content = md_file.read_text().lower()
            for phrase in BUZZWORDS:
                count = content.count(phrase)
                if count > 0:
                    rel = md_file.relative_to(workspace)
                    result.add_warning(
                        f"Buzzword flag in {rel}: '{phrase}' x{count}"
                    )



def check_chosen_angle(workspace: Path, result: GateResult) -> None:
    path = workspace / "strategy/chosen-angle.md"
    if not path.exists():
        return
    content = path.read_text().strip()
    # Require a minimum body size to avoid placeholder files passing.
    if len(content) < 200:
        result.add_warning("strategy/chosen-angle.md looks too short (<200 chars)")



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quality gates for compound-growth output")
    parser.add_argument("--workspace", required=True, help="Workspace path with research/strategy/assets/review")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings in addition to errors",
    )
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    result = GateResult()

    check_required_files(workspace, result)
    check_research_sources(workspace, result)
    check_buzzwords(workspace, result)
    check_chosen_angle(workspace, result)

    print(f"Workspace: {workspace}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")

    if result.errors:
        print("\n[Errors]")
        for item in result.errors:
            print(f"- {item}")

    if result.warnings:
        print("\n[Warnings]")
        for item in result.warnings:
            print(f"- {item}")

    if result.errors:
        print("\nResult: FAIL")
        return 1

    if args.strict and result.warnings:
        print("\nResult: FAIL (strict mode)")
        return 1

    print("\nResult: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
