# 🏗️ Vibe Marketing - Arquitetura

> Documentação técnica completa da skill.

---

## 📐 Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                           │
│              (Codex / Kimi / Antigravity)                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   ORCHESTRATOR                                │
│         (Roteamento, Contexto, Sequenciamento)              │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   RESEARCH   │ │ METHODOLOGY  │ │   STRATEGY   │
│   (MCPs)     │ │ (Frameworks) │ │  (Skills)    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴────────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│    COPY      │ │   CREATIVE   │ │   OUTPUT     │
│  (Skills)    │ │   (Skills)   │ │  (Assets)    │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 🧩 Camadas da Arquitetura

### Camada 1: Research (MCPs)
**Responsabilidade:** Coleta de dados e inteligência de mercado

```
01-research/
├── research-framework.md    # Metodologia de pesquisa
└── competitor-analysis.md   # Análise competitiva

Ferramentas:
├── DuckDuckGo (grátis)     # Busca web
├── BeautifulSoup (grátis)  # Scraping
└── Playwright (grátis)     # Browser automation
```

**Output:** Dados estruturados sobre mercado, concorrência, público

---

### Camada 2: Methodology (Frameworks)
**Responsabilidade:** Princípios e frameworks validados

```
02-methodology/
├── schwartz-stages.md        # Estágios de sofisticação
├── hopkins-principles.md     # Princípios de copy
├── ogilvy-research.md        # Método de pesquisa
└── halbert-starving-crowd.md # Multidão faminta
```

**Output:** Diretrizes estratégicas baseadas em frameworks clássicos

---

### Camada 3: Strategy (Skills)
**Responsabilidade:** Definição de estratégia de marca

```
03-strategy/
├── brand-voice/skill.md      # Voz da marca
├── positioning-angles/skill.md # Ângulos de posicionamento
├── keyword-research/skill.md   # Pesquisa de keywords
└── lead-magnet/skill.md        # Lead magnets
```

**Output:** Estratégia de marca documentada e aplicável

---

### Camada 4: Copy (Skills)
**Responsabilidade:** Criação de copy de alta conversão

```
04-copy/
├── direct-response/skill.md  # Copy direta
├── email-sequences/skill.md  # Sequências de email
├── newsletter/skill.md       # Newsletters
├── seo-content/skill.md      # Conteúdo SEO
└── content-atomizer/skill.md # Atomização
```

**Output:** Copy pronta para uso em múltiplos formatos

---

### Camada 5: Creative (Skills)
**Responsabilidade:** Assets visuais e multimídia

```
05-creative/
├── creative-strategist/skill.md  # Estratégia criativa
├── product-photo/skill.md        # Fotos de produto
├── product-video/skill.md        # Vídeos de produto
├── social-graphics/skill.md      # Gráficos sociais
└── talking-head/skill.md         # Vídeos talking head
```

**Output:** Briefs criativos e assets visuais

---

## 🔧 Sistema de Stacks

Stacks são sequências pré-configuradas de skills.

```
06-stacks/
├── foundation-stack/     # Base da marca
├── conversion-stack/     # Conversão
├── traffic-stack/        # Tráfego
└── nurture-stack/        # Nutrição
```

### Estrutura de um Stack

```yaml
# stack.yaml
name: foundation-stack
description: Fundação completa da marca
version: 1.0.0

sequence:
  - skill: 01-research/research-framework
    output: research-report
  
  - skill: 03-strategy/brand-voice
    input: research-report
    output: brand-voice-guide
  
  - skill: 03-strategy/positioning-angles
    input: brand-voice-guide
    output: positioning-strategy
  
  - skill: 03-strategy/keyword-research
    input: positioning-strategy
    output: keyword-map

output:
  format: consolidated
  location: 08-output/foundation/
```

---

## 🔄 Sistema de Workflows

Workflows são processos completos com checkpoints.

```
07-sequences/
├── 5-stage-build.md      # Processo completo
└── expert-review.md      # Framework de revisão
```

### 5-Stage Build

```
RESEARCH → FOUNDATION → STRUCTURE → ASSETS → ITERATION
    │           │           │          │         │
    ▼           ▼           ▼          ▼         ▼
  10-15m      15-20m      20-30m     30-45m    contínuo
```

---

## 🛠️ Sistema de Ferramentas

```
09-tools/
├── research_tools.py     # Implementação Python
├── requirements.txt      # Dependências
└── setup.sh             # Script de instalação
```

### Arquitetura de Fallback

```
Research:
  DuckDuckGo (grátis) → Brave (grátis) → Perplexity (pago)

Scraping:
  BeautifulSoup (grátis) → Crawl4AI (grátis) → Firecrawl (pago)

Creative:
  Pollinations (grátis) → HuggingFace (grátis) → Glif (pago)
```

### Web Console (Flask + Static UI)

Interface gráfica local para onboarding de IDEs e chaves premium:

```
09-tools/
├── onboard_web.py        # Flask app factory + CLI
├── onboard_api.py        # Normalização/validação de payload
└── web/onboard/
    ├── index.html        # UI estática
    ├── styles.css        # Dark theme styling
    └── app.js            # Fetch API wiring
```

**Endpoints:**
- `GET /api/v1/health` — Status do serviço
- `GET /api/v1/defaults` — IDEs suportadas e shell detectado
- `POST /api/v1/onboard/preview` — Executa dry-run
- `POST /api/v1/onboard/apply` — Aplica mudanças com decisões

**Uso:**
```bash
python3 09-tools/onboard_web.py serve --host 127.0.0.1 --port 8765
```

---

## 💾 Sistema de Contexto

### Checkpoint System

```yaml
# Contexto salvo automaticamente
context:
  session_id: uuid
  stage: current_stage
  data:
    research: {...}
    strategy: {...}
    copy: {...}
  
  checkpoints:
    - stage: research
      timestamp: ISO8601
      hash: checksum
    - stage: foundation
      timestamp: ISO8601
      hash: checksum
```

### Comandos de Contexto

```
@vm-checkpoint-save    # Salva checkpoint atual
@vm-context-save       # Salva contexto completo
@vm-context-load       # Carrega contexto
@vm-continue          # Continua de checkpoint
```

---

## 🔌 Integração com IDEs

### Codex (200k context)

```yaml
# .codex/config.yaml
skills:
  - path: ./vibe-marketing-skill
    command: "@vibe"
    
context_management:
  max_tokens: 180000
  strategy: sliding_window
  
optimizations:
  - lazy_loading: true
  - chunk_size: 4000
```

### Kimi Code (2M context)

```yaml
# .kimi/skills.yaml
skills:
  vibe-marketing:
    path: ./vibe-marketing-skill
    trigger: "/vibe"
    
context_management:
  max_tokens: 1500000
  strategy: full_context
  
optimizations:
  - preload_frameworks: true
```

### Antigravity (Visual)

```yaml
# .antigravity/skills.yaml
skills:
  - name: vibe-marketing
    path: ./vibe-marketing-skill
    prefix: "vibe:"
    
ui:
  - visual_workflows: true
  - drag_drop_stacks: true
```

---

## 📊 Sistema de Output

```
08-output/
└── YYYY-MM-DD-HHMMSS/
    ├── metadata.json           # Metadados da sessão
    ├── research/
    │   ├── competitor-analysis.md
    │   └── market-report.md
    ├── strategy/
    │   ├── brand-voice.md
    │   └── positioning.md
    ├── copy/
    │   ├── landing-page.md
    │   └── email-sequence.md
    ├── creative/
    │   ├── creative-brief.md
    │   └── asset-list.md
    └── final/
        ├── consolidated-brief.md
        └── assets-package.zip
```

---

## 🔐 Configuração

### vibe.config.yaml

```yaml
# Configuração principal
vibe_marketing:
  version: "1.0.0"
  
  # Ferramentas (grátis por padrão)
  tools:
    research:
      primary: duckduckgo
      fallback: brave
    scraping:
      primary: beautifulsoup
      fallback: crawl4ai
    creative:
      primary: pollinations
      fallback: huggingface
  
  # IDE
  ide:
    default: codex
    optimizations:
      codex:
        context_window: 200000
        strategy: sliding_window
      kimi:
        context_window: 2000000
        strategy: full_context
  
  # Output
  output:
    format: markdown
    location: ./08-output
    auto_save: true
  
  # Revisão
  review:
    enabled: true
    stages:
      - copy
      - design
      - strategy
```

---

## 🧪 Testes

```bash
# Testar ferramentas
python 09-tools/research_tools.py --test

# Testar stack
python -m vibe_marketing.test --stack foundation

# Testar workflow
python -m vibe_marketing.test --workflow landing
```

---

## 📈 Performance

| Componente | Tempo Médio | Tokens |
|------------|-------------|--------|
| Research | 10-15 min | ~15k |
| Foundation | 15-20 min | ~20k |
| Structure | 20-30 min | ~25k |
| Assets | 30-45 min | ~35k |
| Review | 10-15 min | ~10k |

---

## 🔗 Referências

- [README.md](README.md) - Visão geral
- [QUICKSTART.md](QUICKSTART.md) - Primeiros passos
- [vibe.config.yaml](vibe.config.yaml) - Configuração

---

<div align="center">

**Arquitetura modular. Escalável. Zero custo obrigatório.**

</div>
