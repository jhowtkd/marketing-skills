from __future__ import annotations


def render_summary(items: list[dict]) -> str:
    lines = ["# VM Onboard Summary", ""]
    for item in items:
        ide = item.get("ide", "unknown")
        status = item.get("status", "unknown")
        lines.append(f"- {ide}: {status}")
    return "\n".join(lines) + "\n"

