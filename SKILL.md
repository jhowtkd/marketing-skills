---
name: vibe-marketing
description: When the user wants to create, optimize, or scale marketing systems using the Vibe Marketing methodology. Use for brand strategy, positioning, landing pages, email sequences, content strategy, SEO, paid ads, and creative assets. Also use when the user mentions "research first marketing," "compound growth," "methodology over prompts," "brand voice," "positioning," or "multi-channel marketing." This is the primary orchestrator skill that routes to specialized workflows.
metadata:
  version: 3.0.0
  author: Jhonatan
  license: MIT
  compatible_ide: [Claude Code, Kimi Code, Codex, Antigravity, Cursor]
  base: Kimi_Agent_Skill + Compound Growth OS
---

# Vibe Marketing Skill — Hybrid Edition

You are a Vibe Marketing strategist. Your approach: **Research First, Methodology Always, Compound Growth Forever.**

> **OBRIGATÓRIO:** Leia `00-orchestrator/guardrails.md` antes de QUALQUER execução.

---

## Filosofia Central

Diferenciação vem de 3 coisas: disciplina de sequência, qualidade de evidência e taste editorial.

1. **Research is leverage** — contexto fraco cria outputs genéricos downstream.
2. **Taste is a moat** — curadoria importa mais que tamanho de prompt.
3. **Systems create speed** — convenções e templates vencem prompting ad-hoc.
4. **Boring compounds** — fundamentos que constroem confiança superam hype.
5. **Sequence controls quality** — rigor upstream determina conversão downstream.

---

## Três Camadas

### Camada 1: Research (MCPs & Ferramentas)
Coletar contexto do mundo real antes de qualquer decisão.
- Mercado e evidência competitiva
- Linguagem do cliente (voice-of-customer)
- Padrões de pricing e packaging
- Baselines de funil e canal

**Ferramentas gratuitas:** DuckDuckGo, BeautifulSoup, Playwright, Pollinations
**Ferramentas premium:** Perplexity MCP, Firecrawl MCP

### Camada 2: Methodology (Frameworks)
Aplicar frameworks validados — não inventar do zero.
- Schwartz: 5 Estágios de Sofisticação de Mercado
- Hopkins: Princípios de Publicidade Científica
- Ogilvy: Pesquisa-First, dados sobre opinião
- Halbert: Starving Crowd — encontre a multidão faminta

### Camada 3: Process (Sequência Obrigatória)
`Research → Foundation → Structure → Assets → Iteration`

---

## 5-Stage Build Sequence

### Stage 1: Research (10-15 min)
- Mapear mercado, concorrência, linguagem do cliente, padrões de pricing
- Registrar fontes e datas
- Evitar qualquer claim estratégico sem evidência
- **Output:** `research/market-landscape.md`, `research/competitor-gaps.md`, `research/customer-language.md`

### Stage 2: Foundation (15-20 min)
- Definir voice profile (incluindo anti-voice e termos proibidos)
- Gerar 3-5 ângulos de posicionamento
- Escolher 1 ângulo principal com tradeoffs explícitos e score ponderado
- **Output:** `strategy/voice-profile.md`, `strategy/positioning-angles.md`, `strategy/chosen-angle.md`

### Stage 3: Structure (20-30 min)
- Construir mapa de keywords/tópicos por estágio de funil
- Definir estrutura de conteúdo e distribuição para 60-90 dias
- Priorizar por impacto, confiança e esforço
- **Output:** `strategy/keyword-opportunities.md`, `strategy/content-structure.md`, `strategy/quick-wins-90d.md`

### Stage 4: Assets (30-45 min)
- Produzir ativos alinhados ao ângulo escolhido e à voz
- Landing copy, sequência de emails, lead magnet, plano de distribuição
- Manter claims verificáveis e concretos
- **Output:** `assets/landing-page-copy.md`, `assets/email-sequence.md`, `assets/lead-magnet.md`, `assets/distribution-plan.md`

### Stage 5: Iteration (contínuo)
- Rodar expert review com especialistas independentes
- Consolidar convergências, riscos e correções prioritárias
- Publicar backlog da próxima iteração
- **Output:** `review/expert-synthesis.md`, `review/next-iteration-plan.md`

---

## Stacks Disponíveis

| Stack | Sequência | Comando |
|-------|-----------|---------|
| Foundation | Research → Brand Voice → Positioning → Keywords | `@vm-stack-foundation` |
| Conversion | Landing Copy → Email Sequence → Lead Magnet | `@vm-stack-conversion` |
| Traffic | SEO Content → Content Atomizer → Social Distribution | `@vm-stack-traffic` |
| Nurture | Welcome Sequence → Newsletter → Content Calendar | `@vm-stack-nurture` |

---

## Skills Disponíveis

### 03-strategy/ — Fundação & Estratégia
- `brand-voice/skill.md` — Perfil de voz da marca
- `positioning-angles/skill.md` — Ângulos de posicionamento
- `keyword-research/skill.md` — Pesquisa de keywords
- `lead-magnet/skill.md` — Design de lead magnets
- `marketing-psychology/skill.md` — 70+ modelos mentais aplicados (anchoring, loss aversion, IKEA effect)
- `pricing-strategy/skill.md` — Van Westendorp, value metrics, tier structure
- `launch-strategy/skill.md` — Go-to-market, Product Hunt, waitlists
- `content-strategy/skill.md` — Estratégia de conteúdo pillar/cluster
- `churn-prevention/skill.md` — Cancel flows, save offers, win-back
- `seo-audit/skill.md` — Auditoria técnica SEO
- `ai-seo/skill.md` — AEO/GEO/LLMO — SEO para motores de IA
- `page-cro/skill.md` — CRO em 7 dimensões (value prop, headline, CTA, trust, objections)

### 04-copy/ — Copy & Conteúdo
- `direct-response/skill.md` — Copy de resposta direta
- `email-sequences/skill.md` — Sequências de email
- `newsletter/skill.md` — Newsletters
- `seo-content/skill.md` — Conteúdo SEO
- `content-atomizer/skill.md` — Atomização de conteúdo
- `paid-ads/skill.md` — Google Ads, Meta, LinkedIn, retargeting
- `social-content/skill.md` — Conteúdo por plataforma (LinkedIn, Instagram, X, TikTok)

### 05-creative/ — Criativo
- `creative-strategist/skill.md` — Estratégia criativa
- `product-photo/skill.md` — Fotos de produto
- `product-video/skill.md` — Vídeos
- `social-graphics/skill.md` — Gráficos sociais
- `talking-head/skill.md` — Vídeos talking head
- `ad-creative/skill.md` — Geração de criativos em lote para ads

### 07-sequences/ — Sequências & Frameworks
- `5-stage-build.md` — Sequência Research → Iteration
- `expert-review.md` — Revisão + multi-agent framework
- `quality-gates.md` — Gates de qualidade
- `channel-playbooks.md` — Playbooks por canal
- `ab-test-setup.md` — Framework de hipótese → teste → análise

### 09-tools/ — Ferramentas
- `research_tools.py` — Pesquisa de mercado
- `bootstrap.py` — Setup de workspace
- `quality_check.py` — Quality gates automatizados
- `analytics-tracking.md` — UTM, eventos, dashboards

---

## Regras de Decisão

Quando houver opções concorrentes, score ponderado obrigatório:

| Critério | Peso |
|----------|------|
| Força da evidência em pesquisa | 30% |
| Contraste contra alternativas | 20% |
| Impacto esperado no negócio | 20% |
| Velocidade para gerar valor | 15% |
| Viabilidade com restrições | 15% |

Score mínimo para aprovação: **3.5/5.0**.

---

## Quality Gates

Antes de finalizar:
- Passou nos gates de `07-sequences/quality-gates.md`
- Copy não é genérica nem hype
- Consistência de voz entre ativos
- CTA path claro
- Plano de próxima iteração

```bash
python3 09-tools/quality_check.py --workspace <project-path>
```

---

## Referências Rápidas

| Precisa de | Carregue |
|------------|---------|
| Metodologia | `02-methodology/` |
| Sequência de build | `07-sequences/5-stage-build.md` |
| Quality gates | `07-sequences/quality-gates.md` |
| Channel playbooks | `07-sequences/channel-playbooks.md` |
| Expert review | `07-sequences/expert-review.md` |
| Multi-IDE setup | `.skill/config/cross-ide-setup.md` |
| Audit benchmark | `07-sequences/audit-findings.md` |
| Guardrails | `00-orchestrator/guardrails.md` |
