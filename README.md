# Vibe Marketing Skill — Hybrid Edition

> [!IMPORTANT]
> Skill de marketing para IDEs de código (Codex, Kimi Code, Antigravity, Cursor).
> Kimi_Agent_Skill (arquitetura) + Compound Growth OS (guardrails) + Corey Haines Marketing Skills (CRO, Pricing, Psychology).

## Uso rápido

```
@vibe Quero criar uma landing page para [produto] para [público].
```

## IDEs suportados

| IDE | Comando | Setup |
|-----|---------|-------|
| **Codex** | `@vibe` | Symlink em `~/.codex/skills/` |
| **Kimi Code** | `/vibe` | Adicionar `SKILL.md` ao Project Knowledge |
| **Antigravity** | `vibe:` | Workflow em `.agents/workflows/` |
| **Cursor** | `@vibe` | Rules ou Agent Mode |

## O que está dentro

### 03-strategy/ (12 skills)
- `brand-voice` — Perfil de voz da marca
- `positioning-angles` — Ângulos de posicionamento
- `keyword-research` — Pesquisa de keywords
- `lead-magnet` — Design de lead magnets
- `marketing-psychology` — 70+ modelos mentais (Corey Haines)
- `pricing-strategy` — Van Westendorp, value metrics, tiers (Corey Haines)
- `launch-strategy` — Go-to-market, Product Hunt, waitlists (Corey Haines)
- `content-strategy` — Pillar/cluster, calendário 90d (Corey Haines)
- `churn-prevention` — Cancel flows, save offers, win-back (Corey Haines)
- `seo-audit` — Auditoria técnica SEO (Corey Haines)
- `ai-seo` — AEO/GEO/LLMO — SEO para motores de IA (Corey Haines)
- `page-cro` — CRO em 7 dimensões (Corey Haines)

### 04-copy/ (7 skills)
- `direct-response` — Copy de resposta direta
- `email-sequences` — Sequências de email
- `newsletter` — Newsletters
- `seo-content` — Conteúdo SEO
- `content-atomizer` — Atomização de conteúdo
- `paid-ads` — Google Ads, Meta, LinkedIn (Corey Haines)
- `social-content` — Conteúdo social por plataforma (Corey Haines)

### 05-creative/ (6 skills)
- `creative-strategist` — Estratégia criativa
- `product-photo`, `product-video`, `social-graphics`, `talking-head`
- `ad-creative` — Criativos de ads em lote (Corey Haines)

### 06-stacks/ (4 stacks YAML)
Foundation · Conversion · Traffic · Nurture

### 07-sequences/ (6 docs)
- `5-stage-build.md` — Research → Foundation → Structure → Assets → Iteration
- `expert-review.md` — Review + multi-agent framework
- `quality-gates.md`, `channel-playbooks.md`, `audit-findings.md`
- `ab-test-setup.md` — Framework de A/B test (Corey Haines)

### 08-templates/ (7 templates)
Landing · Email · SEO · Research · Business Brief · Experiment Log · Weekly Review

### 09-tools/ (9 ferramentas)
- `research_tools.py`, `bootstrap.py`, `quality_check.py`, `onboard.py`
- `analytics-tracking.md` — UTM, eventos, dashboards (Corey Haines)

## Sequência obrigatória

```
Research → Foundation → Structure → Assets → Iteration
```

Leia `00-orchestrator/guardrails.md` antes de qualquer execução.

## Origem dos componentes

| Componente | Origem |
|-----------|--------|
| Arquitetura, stacks, tools | Kimi_Agent_Skill AI para IDEs |
| Quality gates, guardrails, scripts | Compound Growth OS (mkt-codex) |
| Psychology, CRO, Pricing, Paid Ads, Launch, SEO Audit, AI-SEO, Churn, Analytics | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) |

## Comandos

| Categoria | Comandos |
|-----------|---------|
| Fundação | `@vm-research` `@vm-foundation` `@vm-psychology` `@vm-pricing` `@vm-launch` `@vm-content-strategy` `@vm-churn` |
| Copy | `@vm-landing` `@vm-email-seq` `@vm-seo-content` `@vm-ai-seo` `@vm-atomize` `@vm-social` |
| Paid | `@vm-paid-ads` `@vm-ad-creative` |
| CRO | `@vm-page-cro` `@vm-seo-audit` `@vm-ab-test` `@vm-analytics` |
| Review | `@vm-review-copy` `@vm-review-strategy` `@vm-review-all` |
| Stacks | `@vm-stack-foundation` `@vm-stack-conversion` `@vm-stack-traffic` `@vm-stack-nurture` |
| Onboarding | `@vm-onboard` |

## Threaded Foundation Executor (V1)

O stack `@vm-stack-foundation` agora suporta execução híbrida por projeto/thread:
- `research` inicia automaticamente;
- `brand-voice`, `positioning` e `keywords` exigem aprovação manual;
- estado é persistido por `project_id` e `thread_id`;
- logs e artefatos são salvos em `08-output/<date>/<project>/<thread>/`.

### Comandos na thread

- `@vm-stack-foundation` inicia execução até o primeiro gate manual.
- `@vm-approve <stage>` aprova e executa uma etapa manual.
- `@vm-status` retorna estado atual e artefatos.
- `@vm-retry <stage>` reexecuta uma etapa.

### Comandos CLI equivalentes

```bash
python3 09-tools/pipeline_runner.py run \
  --output-root /path/for/artifacts \
  --project-id acme \
  --thread-id th-001 \
  --stack-path 06-stacks/foundation-stack/stack.yaml \
  --query "crm para clínicas"

python3 09-tools/pipeline_runner.py approve --project-id acme --thread-id th-001 --stage brand-voice
python3 09-tools/pipeline_runner.py status --project-id acme --thread-id th-001
python3 09-tools/pipeline_runner.py retry --project-id acme --thread-id th-001 --stage research
```

`--output-root` define onde os artefatos da execução serão gravados e esse caminho fica persistido no estado da thread.

### Providers (premium-first com fallback)

- Primário: Perplexity + Firecrawl.
- Fallback em erro: DuckDuckGo + scraping gratuito.
- Configure: `PERPLEXITY_API_KEY` e `FIRECRAWL_API_KEY`.

### Setup rápido de ambiente

```bash
bash 09-tools/setup.sh --check-only
bash 09-tools/setup.sh --persist-keys
bash 09-tools/setup.sh --run-onboard --onboard-dry-run --onboard-ide codex,cursor,kimi,antigravity
```

`--persist-keys` grava as chaves no profile do shell (`~/.zshrc`/`~/.bashrc`) para uso em novas sessões nessa máquina.

### Onboarding MCP + IDEs (híbrido)

Use `@vm-onboard` para iniciar onboarding guiado (preview/diff por IDE + confirmação de apply/skip).

CLI equivalente:

```bash
python3 09-tools/onboard.py run --dry-run --ide codex,cursor,kimi,antigravity
python3 09-tools/onboard.py run --ide codex,cursor --decision codex=apply --decision cursor=skip
python3 09-tools/onboard.py run --yes --apply-keys --shell-file ~/.zshrc
```
