from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _extract_first_artifact_content(workspace_root: Path, run_id: str, fallback_text: str) -> str:
    stages_root = workspace_root / "runs" / run_id / "stages"
    if not stages_root.exists():
        return fallback_text
    for stage_dir in sorted(stages_root.iterdir()):
        manifest_path = stage_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifacts = payload.get("artifacts", [])
        if not isinstance(artifacts, list) or not artifacts:
            continue
        first = artifacts[0]
        if isinstance(first, str):
            target = stage_dir / first
        elif isinstance(first, dict):
            raw = first.get("path") or first.get("filename")
            target = stage_dir / str(raw) if raw else None
        else:
            target = None
        if target is None or not target.exists():
            continue
        try:
            return target.read_text(encoding="utf-8")
        except Exception:
            continue
    return fallback_text


def _compute_heuristic_score(markdown: str) -> dict[str, Any]:
    text = markdown.strip()
    words = len([token for token in text.replace("\n", " ").split(" ") if token])
    heading_count = sum(1 for line in text.splitlines() if line.strip().startswith("#"))
    list_count = sum(1 for line in text.splitlines() if line.strip().startswith(("-", "*")))
    lower = text.lower()

    cta_keywords = ["cta", "clique", "cadastre", "agende", "compre", "responda"]
    action_keywords = ["defina", "liste", "execute", "publique", "teste", "otimize"]
    cta_hits = sum(1 for key in cta_keywords if key in lower)
    action_hits = sum(1 for key in action_keywords if key in lower)

    completude = min(100, max(0, 20 + min(60, words // 4)))
    estrutura = min(100, max(0, heading_count * 20 + list_count * 12))
    clareza = 80 if words >= 40 else 50 if words >= 15 else 25
    cta = min(100, cta_hits * 30 + action_hits * 8)
    acionabilidade = min(100, list_count * 18 + action_hits * 15 + cta_hits * 8)

    criteria = {
        "completude": completude,
        "estrutura": estrutura,
        "clareza": clareza,
        "cta": cta,
        "acionabilidade": acionabilidade,
    }
    overall = round(sum(criteria.values()) / len(criteria))

    recommendations: list[str] = []
    if completude < 60:
        recommendations.append("Aumente contexto e detalhamento da entrega.")
    if estrutura < 60:
        recommendations.append("Estruture com titulos e blocos de leitura.")
    if cta < 60:
        recommendations.append("Inclua CTA explicito com proximo passo.")
    if acionabilidade < 60:
        recommendations.append("Adicione itens acionaveis com verbos de acao.")

    return {
        "overall": overall,
        "criteria": criteria,
        "recommendations": recommendations,
    }


def _attempt_deep_evaluation(_markdown: str, _rubric_version: str) -> dict[str, Any]:
    raise RuntimeError("deep evaluation unavailable")


def evaluate_run_quality(
    *,
    run_id: str,
    request_text: str,
    workspace_root: Path,
    depth: str,
    rubric_version: str,
) -> dict[str, Any]:
    content = _extract_first_artifact_content(workspace_root, run_id, fallback_text=request_text)
    heuristic = _compute_heuristic_score(content)

    response = {
        "run_id": run_id,
        "depth": depth,
        "rubric_version": rubric_version,
        "content_length": len(content),
        "score": {**heuristic, "source": "heuristic"},
        "fallback_applied": False,
    }

    if depth != "deep":
        return response

    try:
        deep = _attempt_deep_evaluation(content, rubric_version)
        response["score"] = {**deep, "source": "deep"}
        return response
    except Exception as exc:
        response["fallback_applied"] = True
        response["fallback_reason"] = str(exc)
        return response
