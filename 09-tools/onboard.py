#!/usr/bin/env python3
"""Vibe Marketing onboarding orchestrator (MCP + IDE setup)."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime
from difflib import unified_diff
from importlib import import_module
import json
import os
from pathlib import Path
import shutil
import tempfile

from onboard_report import render_summary


SUPPORTED_IDES = ("codex", "cursor", "kimi", "antigravity")
PREMIUM_KEYS = ("PERPLEXITY_API_KEY", "FIRECRAWL_API_KEY")


def _adapter_module_name(ide: str) -> str:
    return f"onboard_adapters.{ide}"


def load_adapter(ide: str):
    if ide not in SUPPORTED_IDES:
        raise ValueError(f"Unsupported IDE: {ide}")
    return import_module(_adapter_module_name(ide))


def discover_targets(ide_csv: str) -> list[dict]:
    if ide_csv.strip():
        requested = [item.strip().lower() for item in ide_csv.split(",") if item.strip()]
    else:
        requested = list(SUPPORTED_IDES)

    unique = OrderedDict((ide, None) for ide in requested)
    targets: list[dict] = []
    home = Path.home()

    for ide in unique.keys():
        adapter = load_adapter(ide)
        targets.append(
            {
                "ide": ide,
                "status": "detected",
                "target_paths": [str(p) for p in adapter.default_target_paths(home)],
            }
        )
    return targets


def build_diff_preview(before: str, after: str, target: str) -> str:
    diff_lines = unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=target,
        tofile=target,
    )
    return "".join(diff_lines)


def apply_change(target: Path, new_content: str) -> dict:
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    backup_path = ""
    existed = target_path.exists()
    previous_content = ""
    if existed:
        previous_content = target_path.read_text(encoding="utf-8")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_candidate = target_path.with_name(f"{target_path.name}.bak.{timestamp}")
        shutil.copy2(target_path, backup_candidate)
        backup_path = str(backup_candidate)

    if (not existed) or previous_content != new_content:
        target_path.write_text(new_content, encoding="utf-8")
        status = "applied"
    else:
        status = "unchanged"

    return {
        "status": status,
        "target_path": str(target_path),
        "backup_path": backup_path,
    }


def _escape_single_quotes(value: str) -> str:
    return value.replace("'", "'\"'\"'")


def _build_profile_content(existing_content: str, var_name: str, var_value: str) -> str:
    lines = existing_content.splitlines()
    filtered = [line for line in lines if not line.startswith(f"export {var_name}=")]
    filtered.append(f"export {var_name}='{_escape_single_quotes(var_value)}'")
    return "\n".join(filtered).strip() + "\n"


def upsert_export(profile_path: Path, var_name: str, var_value: str) -> None:
    profile = Path(profile_path).expanduser()
    profile.parent.mkdir(parents=True, exist_ok=True)
    if not profile.exists():
        profile.write_text("", encoding="utf-8")

    previous = profile.read_text(encoding="utf-8")
    new_content = _build_profile_content(previous, var_name, var_value)

    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as tmp:
        tmp.write(new_content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(profile)


def _resolve_target_path(raw_target: str, ide: str, target_root: Path | None) -> Path:
    source = Path(raw_target).expanduser()
    if target_root is None:
        return source
    return Path(target_root) / ide / source.name


def _detect_shell_profile(shell_file: str) -> Path:
    if shell_file:
        return Path(shell_file).expanduser()

    shell = os.environ.get("SHELL", "")
    if shell.endswith("zsh"):
        return Path.home() / ".zshrc"
    if shell.endswith("bash"):
        return Path.home() / ".bashrc"
    return Path.home() / ".profile"


def _status_from_changes(change_statuses: list[str], decision: str, dry_run: bool) -> str:
    if dry_run:
        return "preview"
    if decision == "skip":
        return "skipped"
    if decision != "apply":
        return "manual_required"
    if any(status == "applied" for status in change_statuses):
        return "applied"
    if change_statuses and all(status == "unchanged" for status in change_statuses):
        return "unchanged"
    if any(status == "failed" for status in change_statuses):
        return "failed"
    return "manual_required"


def run_onboarding(
    ide_csv: str,
    dry_run: bool,
    auto_apply: bool,
    decisions: dict[str, str],
    shell_file: str,
    key_values: dict[str, str],
    apply_keys: bool,
    target_root: Path | None = None,
) -> dict:
    requested_decisions = {key.lower(): value.lower() for key, value in decisions.items()}
    result = {
        "ides": OrderedDict(),
        "keys": OrderedDict(),
        "dry_run": dry_run,
        "auto_apply": auto_apply,
        "shell_file": str(_detect_shell_profile(shell_file)),
    }
    skill_dir = Path(__file__).resolve().parents[1]
    targets = discover_targets(ide_csv)

    for target in targets:
        ide = target["ide"]
        adapter = load_adapter(ide)
        decision = "apply" if auto_apply else requested_decisions.get(ide, "skip")
        ide_report = {
            "ide": ide,
            "decision": decision,
            "status": "skipped",
            "changes": [],
        }
        try:
            planned_changes = adapter.plan_changes(skill_dir)
            for planned in planned_changes:
                resolved_target = _resolve_target_path(
                    planned.get("target_path", ""),
                    ide=ide,
                    target_root=target_root,
                )
                before = resolved_target.read_text(encoding="utf-8") if resolved_target.exists() else ""
                after = planned.get("proposed_content", "")
                diff = build_diff_preview(before=before, after=after, target=str(resolved_target))
                item_report = {
                    "target_path": str(resolved_target),
                    "description": planned.get("description", ""),
                    "diff": diff,
                    "status": "preview",
                    "backup_path": "",
                }

                if not dry_run:
                    if decision == "apply":
                        apply_result = apply_change(resolved_target, after)
                        item_report.update(apply_result)
                    elif decision == "skip":
                        item_report["status"] = "skipped"
                    else:
                        item_report["status"] = "manual_required"

                ide_report["changes"].append(item_report)

            ide_report["status"] = _status_from_changes(
                [item["status"] for item in ide_report["changes"]],
                decision=decision,
                dry_run=dry_run,
            )
        except Exception as exc:  # pragma: no cover - defensive branch
            ide_report["status"] = "failed"
            ide_report["error"] = str(exc)

        result["ides"][ide] = ide_report

    profile_path = _detect_shell_profile(shell_file)
    if key_values:
        existing_profile = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
        for key_name, key_value in key_values.items():
            key_report = {
                "status": "skipped",
                "profile_path": str(profile_path),
                "diff": "",
            }

            if dry_run:
                preview_after = _build_profile_content(existing_profile, key_name, key_value)
                key_report["status"] = "preview"
                key_report["diff"] = build_diff_preview(
                    before=existing_profile,
                    after=preview_after,
                    target=str(profile_path),
                )
                existing_profile = preview_after
            elif apply_keys or auto_apply:
                upsert_export(profile_path, key_name, key_value)
                key_report["status"] = "applied"

            result["keys"][key_name] = key_report

    return result


def _parse_decisions(values: list[str]) -> dict[str, str]:
    decisions: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            continue
        ide, decision = raw.split("=", 1)
        normalized_decision = decision.strip().lower()
        if normalized_decision not in {"apply", "skip"}:
            continue
        decisions[ide.strip().lower()] = normalized_decision
    return decisions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser("vm-onboard")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--yes", action="store_true")
    run_parser.add_argument("--ide", default="")
    run_parser.add_argument("--shell-file", default="")
    run_parser.add_argument("--decision", action="append", default=[])
    run_parser.add_argument("--apply-keys", action="store_true")
    run_parser.add_argument("--perplexity-key", default="")
    run_parser.add_argument("--firecrawl-key", default="")
    run_parser.add_argument("--target-root", default="")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        key_values: dict[str, str] = {}
        if args.perplexity_key:
            key_values["PERPLEXITY_API_KEY"] = args.perplexity_key
        elif args.apply_keys and os.environ.get("PERPLEXITY_API_KEY"):
            key_values["PERPLEXITY_API_KEY"] = os.environ["PERPLEXITY_API_KEY"]

        if args.firecrawl_key:
            key_values["FIRECRAWL_API_KEY"] = args.firecrawl_key
        elif args.apply_keys and os.environ.get("FIRECRAWL_API_KEY"):
            key_values["FIRECRAWL_API_KEY"] = os.environ["FIRECRAWL_API_KEY"]

        target_root = Path(args.target_root).expanduser() if args.target_root else None
        report = run_onboarding(
            ide_csv=args.ide,
            dry_run=args.dry_run,
            auto_apply=args.yes,
            decisions=_parse_decisions(args.decision),
            shell_file=args.shell_file,
            key_values=key_values,
            apply_keys=args.apply_keys,
            target_root=target_root,
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        print(render_summary([item for item in report["ides"].values()]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
