# 🎯 Vibe Marketing Orchestrator

> Sistema de roteamento inteligente para skills de marketing.
> **OBRIGATÓRIO:** Antes de qualquer execução, leia `00-orchestrator/guardrails.md`.

---

## ⚠️ Regras de Entrada (Obrigatórias)

1. **Leia `guardrails.md`** antes de produzir qualquer output.
2. **Colete inputs necessários** antes de gerar recomendações:
   - Modelo de negócio e oferta
   - ICP (quem compra, contexto de compra)
   - Estado atual (do zero vs ativos existentes)
   - Meta de conversão e horizonte de tempo
   - Concorrentes e canais conhecidos
   - Restrições (budget, time, compliance, marca)
3. **Sequência obrigatória:** `Research → Foundation → Structure → Assets → Iteration`. Não pule etapas.
4. **Carregamento seletivo:** Carregue apenas os arquivos necessários para a etapa atual.

---

## 🚀 Ponto de Entrada

Bem-vindo ao **Vibe Marketing**! Este é o orchestrator - seu ponto de entrada para criar campanhas de marketing de alta performance.

---

## 📋 Como Usar

### Comando Principal

```
@vibe [sua solicitação]
```

O orchestrator vai:
1. **Analisar** sua solicitação
2. **Identificar** o workflow ou skill necessário
3. **Rotear** para o componente correto
4. **Coordenar** a execução
5. **Entregar** o resultado consolidado

---

## 🎮 Comandos Disponíveis

### Fundação & Estratégia

| Comando | Skill | Descrição |
|---------|-------|-----------|
| `@vm-research` | `01-research` | Pesquisa de mercado completa |
| `@vm-foundation` | `03-strategy/brand-voice` | Brand voice + positioning |
| `@vm-psychology` | `03-strategy/marketing-psychology` | 70+ modelos mentais aplicados |
| `@vm-pricing` | `03-strategy/pricing-strategy` | Pricing, tiers, Van Westendorp |
| `@vm-launch` | `03-strategy/launch-strategy` | Go-to-market, Product Hunt, waitlists |
| `@vm-content-strategy` | `03-strategy/content-strategy` | Pillar/cluster, calendário 90d |
| `@vm-churn` | `03-strategy/churn-prevention` | Cancel flows, save offers, win-back |

### Copy & Conteúdo

| Comando | Skill | Descrição |
|---------|-------|-----------|
| `@vm-landing` | `04-copy/direct-response` | Landing page completa |
| `@vm-email-seq` | `04-copy/email-sequences` | Sequência de emails |
| `@vm-seo-content` | `04-copy/seo-content` | Artigo SEO |
| `@vm-ai-seo` | `03-strategy/ai-seo` | SEO para IA (AEO/GEO/LLMO) |
| `@vm-atomize` | `04-copy/content-atomizer` | 1 conteúdo → 15+ derivados |
| `@vm-social` | `04-copy/social-content` | Conteúdo social por plataforma |

### Paid Media & Criativo

| Comando | Skill | Descrição |
|---------|-------|-----------|
| `@vm-paid-ads` | `04-copy/paid-ads` | Campanha Google/Meta/LinkedIn |
| `@vm-ad-creative` | `05-creative/ad-creative` | Criativos em lote para ads |

### CRO & Testes

| Comando | Skill | Descrição |
|---------|-------|-----------|
| `@vm-page-cro` | `03-strategy/page-cro` | CRO em 7 dimensões (qualquer página) |
| `@vm-seo-audit` | `03-strategy/seo-audit` | Auditoria técnica SEO |
| `@vm-ab-test` | `07-sequences/ab-test-setup` | Hipótese → teste → análise |
| `@vm-analytics` | `09-tools/analytics-tracking` | UTM, eventos, dashboards |

### Stacks Pré-Configuradas

| Comando | Descrição | Output |
|---------|-----------|--------|
| `@vm-stack-foundation` | Fundação da marca | Brand Voice + Positioning + Keywords |
| `@vm-stack-conversion` | Conversão | Landing + Emails + Lead Magnet |
| `@vm-stack-traffic` | Tráfego | SEO + Social + Ads |
| `@vm-stack-nurture` | Nutrição | Welcome + Newsletter + Content |

### Revisão Especializada

| Comando | Descrição |
|---------|-----------|
| `@vm-review-copy` | Revisão de copywriting |
| `@vm-review-design` | Revisão de design |
| `@vm-review-strategy` | Revisão de estratégia |
| `@vm-review-all` | Revisão completa |

### Gerenciamento de Contexto

| Comando | Descrição |
|---------|-----------|
| `@vm-checkpoint-save` | Salva checkpoint atual |
| `@vm-context-save` | Salva contexto completo |
| `@vm-context-load` | Carrega contexto salvo |
| `@vm-continue` | Continua de checkpoint |

---

## 🔍 Sistema de Roteamento

```
Entrada do Usuário
       │
       ▼
┌──────────────┐
│   Análise    │
│  de Intenção │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────┐
│         CLASSIFICAÇÃO               │
├─────────────────────────────────────┤
│ • research → @vm-research           │
│ • foundation → @vm-foundation       │
│ • landing → @vm-landing             │
│ • email → @vm-email-seq             │
│ • seo → @vm-seo-content             │
│ • atomize → @vm-atomize             │
│ • stack:X → @vm-stack-X             │
│ • review:X → @vm-review-X           │
└─────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│   Execução   │
│   da Skill   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Quality     │
│  Gate Check  │
└──────┬───────┘
       │
       ▼
   RESULTADO
```

---

## 📊 Fluxo de Trabalho Completo (5-Stage Build)

```
┌─────────┐    ┌───────────┐    ┌──────────┐    ┌────────┐    ┌──────────┐
│RESEARCH │───▶│FOUNDATION │───▶│STRUCTURE │───▶│ASSETS  │───▶│ITERATION │
│ 10-15m  │    │  15-20m   │    │  20-30m  │    │ 30-45m │    │ contínuo │
└─────────┘    └───────────┘    └──────────┘    └────────┘    └──────────┘
     │               │               │              │              │
     ▼               ▼               ▼              ▼              ▼
  Mercado        Brand Voice      Copy          Creative      Otimização
  Concorrência   Positioning      Estrutura     Assets        Testes
  Público        Keywords         Frameworks    Briefs        Iteração
```

---

## 🛠️ Ferramentas Integradas

Todas as ferramentas são **gratuitas** por padrão:

| Categoria | Ferramenta | Uso |
|-----------|------------|-----|
| Research | DuckDuckGo | Busca web |
| Scraping | BeautifulSoup | Extração de dados |
| Browser | Playwright | Automação |
| Creative | Pollinations | Imagens |
| QA | quality_check.py | Quality gates |
| Bootstrap | bootstrap.py | Setup de workspace |

---

## 📁 Estrutura de Output

Todo output é salvo em `08-output/YYYY-MM-DD/`:

```
08-output/
└── 2026-02-22/
    ├── metadata.json
    ├── research/
    ├── strategy/
    ├── assets/
    ├── review/
    └── final/
```
