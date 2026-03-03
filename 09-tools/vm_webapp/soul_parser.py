from __future__ import annotations

from typing import Optional

from vm_webapp.soul_templates import required_sections


class SoulParseError(ValueError):
    """Raised when a soul markdown document is invalid."""


def parse_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    order: list[str] = []
    current_section: Optional[str] = None

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            section = line[3:].strip()
            if not section:
                raise SoulParseError("Invalid heading: section title cannot be empty.")
            if section in sections:
                raise SoulParseError(f"Duplicate section heading: '{section}'.")
            current_section = section
            sections[section] = []
            order.append(section)
            continue
        if current_section is not None:
            sections[current_section].append(raw_line)

    parsed: dict[str, str] = {}
    for section in order:
        content = "\n".join(sections[section]).strip()
        parsed[section] = content
    return parsed


def parse_and_validate(level: str, markdown: str) -> dict[str, str]:
    parsed = parse_sections(markdown)
    required = required_sections(level)
    missing = [name for name in required if not parsed.get(name, "").strip()]
    if missing:
        missing_str = ", ".join(missing)
        raise SoulParseError(
            f"Missing required section(s) for level '{level}': {missing_str}."
        )
    return parsed
