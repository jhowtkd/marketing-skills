from __future__ import annotations

from typing import Any

from stack_loader import load_stack as _load_stack


def load_stack(path: str) -> dict[str, Any]:
    return _load_stack(path)


def build_context_pack(
    *,
    brand_soul_md: str,
    product_essence_md: str,
    retrieved: list[dict[str, str]],
    stage_contract: str,
    user_request: str,
) -> str:
    retrieved_sections = []
    for item in retrieved:
        title = item.get("title", "retrieved")
        text = item.get("text", "")
        retrieved_sections.append(f"### {title}\n{text}".strip())

    retrieved_block = "\n\n".join(retrieved_sections) if retrieved_sections else "(none)"
    sections = [
        "# Brand Soul",
        brand_soul_md.strip(),
        "",
        "# Product Essence",
        product_essence_md.strip(),
        "",
        "# Retrieved Context",
        retrieved_block,
        "",
        "# Stage Contract",
        stage_contract.strip(),
        "",
        "# User Request",
        user_request.strip(),
    ]
    return "\n".join(sections).strip() + "\n"
