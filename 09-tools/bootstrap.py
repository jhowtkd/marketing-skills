#!/usr/bin/env python3
"""Bootstrap a compound-growth workspace with standard folders and files."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

REQUIRED_DIRS = [
    "research",
    "strategy",
    "assets",
    "review",
    "ops",
]

SCAFFOLD_FILES_PT = {
    "research/market-landscape.md": "# Panorama de Mercado\n\n## Categorias\n\n## Principais Concorrentes\n\n## Observações\n",
    "research/competitor-gaps.md": "# Gaps de Concorrência\n\n## Mensagens dos Concorrentes\n\n## Espaços em Branco\n\n## Implicações\n",
    "research/customer-language.md": "# Linguagem do Cliente\n\n## Frases de Dor\n\n## Objeções\n\n## Resultados Desejados\n",
    "research/pricing-packaging.md": "# Preço e Packaging\n\n## Preço dos Concorrentes\n\n## Padrões de Oferta\n\n## Oportunidades\n",
    "strategy/voice-profile.md": "# Perfil de Voz\n\n## Resumo\n\n## Palavras para Usar\n\n## Palavras para Evitar\n\n## Reescritas\n",
    "strategy/positioning-angles.md": "# Ângulos de Posicionamento\n\n## Ângulo 1\n\n## Ângulo 2\n\n## Ângulo 3\n",
    "strategy/chosen-angle.md": "# Ângulo Escolhido\n\n## Seleção\n\n## Racional\n\n## Riscos\n",
    "strategy/keyword-opportunities.md": "# Oportunidades de Keyword\n\n| Keyword | Intenção | Estágio de Funil | Prioridade |\n| --- | --- | --- | --- |\n",
    "strategy/content-structure.md": "# Estrutura de Conteúdo\n\n## Pilares\n\n## Clusters\n\n## Caminhos de Distribuição\n",
    "strategy/quick-wins-90d.md": "# Quick Wins (90 Dias)\n\n| Iniciativa | Impacto | Confiança | Esforço | Responsável |\n| --- | --- | --- | --- | --- |\n",
    "assets/landing-page-copy.md": "# Copy de Landing Page\n\n## Hero\n\n## Problema\n\n## Solução\n\n## Prova\n\n## CTA\n",
    "assets/email-sequence.md": "# Sequência de Email\n\n## Visão Geral\n\n## Email 1\n\n## Email 2\n",
    "assets/lead-magnet.md": "# Lead Magnet\n\n## Conceito\n\n## Promessa\n\n## Plano de Entrega\n",
    "assets/distribution-plan.md": "# Plano de Distribuição\n\n## Orgânico\n\n## Pago\n\n## Email\n",
    "review/expert-synthesis.md": "# Síntese de Especialistas\n\n## Convergências\n\n## Divergências\n\n## Correções Prioritárias\n",
    "review/rejection-notes.md": "# Notas de Rejeição\n\n## Sugestões Rejeitadas\n\n## Motivo\n",
    "review/next-iteration-plan.md": "# Plano da Próxima Iteração\n\n| Ação | Responsável | Prazo | Impacto Esperado |\n| --- | --- | --- | --- |\n",
}

SCAFFOLD_FILES_EN = {
    "research/market-landscape.md": "# Market Landscape\n\n## Categories\n\n## Key Competitors\n\n## Observations\n",
    "research/competitor-gaps.md": "# Competitor Gaps\n\n## Competitor Messaging\n\n## White Space Opportunities\n\n## Implications\n",
    "research/customer-language.md": "# Customer Language\n\n## Pain Phrases\n\n## Objections\n\n## Desired Outcomes\n",
    "research/pricing-packaging.md": "# Pricing and Packaging\n\n## Competitor Pricing\n\n## Packaging Patterns\n\n## Offer Opportunities\n",
    "strategy/voice-profile.md": "# Voice Profile\n\n## Voice Summary\n\n## Words to Use\n\n## Words to Avoid\n\n## Rewrite Examples\n",
    "strategy/positioning-angles.md": "# Positioning Angles\n\n## Angle 1\n\n## Angle 2\n\n## Angle 3\n",
    "strategy/chosen-angle.md": "# Chosen Angle\n\n## Selected Angle\n\n## Rationale\n\n## Risks\n",
    "strategy/keyword-opportunities.md": "# Keyword Opportunities\n\n| Keyword | Intent | Funnel Stage | Priority |\n| --- | --- | --- | --- |\n",
    "strategy/content-structure.md": "# Content Structure\n\n## Pillars\n\n## Topic Clusters\n\n## Distribution Paths\n",
    "strategy/quick-wins-90d.md": "# Quick Wins (90 Days)\n\n| Initiative | Impact | Confidence | Effort | Owner |\n| --- | --- | --- | --- | --- |\n",
    "assets/landing-page-copy.md": "# Landing Page Copy\n\n## Hero\n\n## Problem\n\n## Solution\n\n## Proof\n\n## CTA\n",
    "assets/email-sequence.md": "# Email Sequence\n\n## Sequence Overview\n\n## Email 1\n\n## Email 2\n",
    "assets/lead-magnet.md": "# Lead Magnet\n\n## Concept\n\n## Promise\n\n## Delivery Plan\n",
    "assets/distribution-plan.md": "# Distribution Plan\n\n## Organic\n\n## Paid\n\n## Email\n",
    "review/expert-synthesis.md": "# Expert Synthesis\n\n## Areas of Agreement\n\n## Areas of Disagreement\n\n## Priority Fixes\n",
    "review/rejection-notes.md": "# Rejection Notes\n\n## Rejected Suggestions\n\n## Why Rejected\n",
    "review/next-iteration-plan.md": "# Next Iteration Plan\n\n| Action | Owner | Deadline | Expected Impact |\n| --- | --- | --- | --- |\n",
}

TEMPLATE_MAP = {
    "business-brief.md": "strategy/business-brief.md",
    "experiment-log.md": "review/experiment-log.md",
    "weekly-review.md": "review/weekly-review.md",
}


def write_file(path: Path, content: str, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def load_template(templates_dir: Path, template_name: str, project_name: str) -> str:
    template_path = templates_dir / template_name
    if not template_path.exists():
        return ""
    content = template_path.read_text()
    content = content.replace("{{PROJECT_NAME}}", project_name)
    content = content.replace("{{DATE}}", str(date.today()))
    return content


def get_scaffold(lang: str) -> dict[str, str]:
    if lang == "en-us":
        return SCAFFOLD_FILES_EN
    return SCAFFOLD_FILES_PT


def bootstrap(workspace: Path, project_name: str, force: bool, lang: str) -> tuple[int, int]:
    created = 0
    skipped = 0
    scaffold_files = get_scaffold(lang)

    for dirname in REQUIRED_DIRS:
        (workspace / dirname).mkdir(parents=True, exist_ok=True)

    for rel_path, content in scaffold_files.items():
        changed = write_file(workspace / rel_path, content, force)
        created += int(changed)
        skipped += int(not changed)

    templates_dir = Path(__file__).resolve().parent.parent / "assets" / "templates"
    for template_name, target_path in TEMPLATE_MAP.items():
        content = load_template(templates_dir, template_name, project_name)
        if not content:
            skipped += 1
            continue
        changed = write_file(workspace / target_path, content, force)
        created += int(changed)
        skipped += int(not changed)

    return created, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap a compound growth workspace")
    parser.add_argument("--workspace", required=True, help="Path to the project workspace")
    parser.add_argument("--project-name", default="project", help="Project name for templates")
    parser.add_argument("--lang", choices=["pt-br", "en-us"], default="pt-br", help="Scaffold language")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    created, skipped = bootstrap(workspace, args.project_name, args.force, args.lang)
    print(f"Workspace: {workspace}")
    print(f"Language: {args.lang}")
    print(f"Created/updated files: {created}")
    print(f"Skipped existing files: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
