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

## VM Web App Event-Driven Workspace (v2 Async)

O VM Web App agora roda workflow assíncrono por thread com fila interna, execução Foundation-backed e gates críticos de aprovação.

### Subir localmente

```bash
uv run python -m vm_webapp serve --host 127.0.0.1 --port 8766
```

Acesse: `http://127.0.0.1:8766`

### Studio (Guided-first, recomendado)

O Studio é o caminho rápido para criar planos/calendários sem expor a arquitetura interna.

1. Crie/seleciona `Brand` e `Project`.
2. Clique em **Create plan**.
3. Preencha o brief, escolha o playbook (`plan_90d` ou `content_calendar`) e clique em **Generate**.
4. Acompanhe **Status** e **Progress** no Studio e leia o output no **Preview**.
5. Se precisar de detalhes técnicos (IDs, timeline, workflow IO, `skill_overrides`), ative **Dev mode**.

### Fluxo operacional (Dev mode / avançado)

1. Crie `Brand -> Project -> Thread`.
2. Escolha `mode` e, opcionalmente, passe `skill_overrides` no run.
3. O runtime resolve contrato imutável por run:
   - `requested_mode` = modo pedido pelo cliente.
   - `effective_mode` = modo realmente executado (fallback atual: `foundation_stack`).
   - `profile_version` e `fallback_applied`.
4. O run inicia como `queued` e evolui para `running`.
5. Se etapa crítica exigir gate, o run fica em `waiting_approval`.
6. Após `ApprovalGranted`, o runtime auto-retoma sem `/resume` manual e segue até `completed` ou `failed`.

### Profiles de workflow

- Arquivo versionado: `09-tools/vm_webapp/workflow_profiles.yaml`
- Contrato por stage:
  - `key`
  - `skills[]`
  - `approval_required`
  - `retry_policy` (`max_attempts`, `backoff_seconds`)
  - `timeout_seconds`

### Endpoints principais (v2)

- `GET /api/v2/workflow-profiles`
- `POST /api/v2/threads/{thread_id}/workflow-runs` -> retorna `{ run_id, status, requested_mode, effective_mode }`
- `GET /api/v2/workflow-runs/{run_id}`
- `POST /api/v2/workflow-runs/{run_id}/resume` (controle idempotente de seguranca; em run terminal retorna status atual)
- `GET /api/v2/workflow-runs/{run_id}/artifacts`
- `GET /api/v2/workflow-runs/{run_id}/artifact-content?stage_dir=...&artifact_path=...`

### Managed-First Deploy (Render)

Contrato de deploy operacional (API + worker) para ambiente managed-first:

- Blueprint Render: `deploy/render/vm-webapp-render.yaml`
- Runbook operacional: `docs/runbooks/vm-webapp-managed-first.md`
- API command: `uv run python -m vm_webapp serve --host 0.0.0.0 --port $PORT`
- Worker command: `uv run python -m vm_webapp worker --poll-interval-ms 500`

Variaveis obrigatorias em managed mode:

- `VM_ENABLE_MANAGED_MODE=true`
- `VM_DB_URL=<postgres_connection_string>`
- `VM_REDIS_URL=<redis_connection_string>`

Probes recomendadas no deploy:

- `GET /api/v2/health/live`
- `GET /api/v2/health/ready`

### Hierarchical Domain & Tooling (v2 Core)

A plataforma evoluiu para suportar domínio hierárquico completo e governança de ferramentas.

- **Hierarquia:** `Brand -> Campaign -> Task -> Thread -> Run`.
- **Contexto Imutável:** Resolução hierárquica `Brand -> Campaign -> Task` com políticas de override controladas e snapshot imutável por `Run`.
- **Tool Registry:** Catálogo de ferramentas plugáveis com contrato `ToolContract`.
- **Governança:** Autorização por `brand_id`, rate-limit diário e gestão de `ToolCredentialRef`.
- **RAG Pipeline:** Ingestão e recuperação hierárquica (filtro por `brand`, boost por `campaign`) usando `MemoryIndex`.
- **Resiliência:** Políticas de `Retry` com backoff, `FallbackChain` entre providers e `CircuitBreaker`.
- **Observabilidade:** Coletor de métricas de latência, custo e saúde operacional por stage/run.

#### Endpoints de Domínio (v2)

- `POST /api/v2/campaigns`
- `GET /api/v2/campaigns?project_id=...`
- `POST /api/v2/tasks`
- `GET /api/v2/threads/{thread_id}/tasks`

Observação: endpoints de escrita usam header `Idempotency-Key`.

### Estrutura de artifacts por execução

```
runtime/vm/runs/<run_id>/
├── run.json
├── plan.json
└── stages/
    └── <ordem>-<stage_key>/
        ├── manifest.json
        ├── input.json
        ├── output.json
        └── artifacts/
```

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

### Onboarding GUI local (Web Console)

Para uma interface gráfica interativa:

```bash
python3 09-tools/onboard_web.py serve
```

Acesse em `http://127.0.0.1:8765` — selecione IDEs, configure chaves premium, visualize diffs e aplique mudanças com um clique.

`--persist-keys` grava as chaves no profile do shell (`~/.zshrc`/`~/.bashrc`) para uso em novas sessões nessa máquina.

### Onboarding MCP + IDEs (híbrido)

Use `@vm-onboard` para iniciar onboarding guiado (preview/diff por IDE + confirmação de apply/skip).

CLI equivalente:

```bash
python3 09-tools/onboard.py run --dry-run --ide codex,cursor,kimi,antigravity
python3 09-tools/onboard.py run --ide codex,cursor --decision codex=apply --decision cursor=skip
python3 09-tools/onboard.py run --yes --apply-keys --shell-file ~/.zshrc
```

### Configuração LLM para VM Web App

O VM Web App suporta execução com LLM real (Kimi) para geração de artefatos Foundation e chat. Quando configurado, os estágios `research`, `brand-voice`, `positioning`, `keywords` e o `final foundation brief` são gerados via LLM em vez de placeholders estáticos.

**Variáveis de ambiente (.env):**

```bash
KIMI_API_KEY=your_key_here
KIMI_MODEL=kimi-for-coding
KIMI_BASE_URL=https://api.kimi.com/coding/v1
```

**Comportamento:**
- **LLM ativo:** Quando `KIMI_API_KEY` está configurado, os artefatos de cada estágio são gerados via LLM com prompts especializados.
- **LLM inativo:** Se `KIMI_API_KEY` estiver vazio/ausente, o sistema usa conteúdo estático/fallback do executor Foundation.
- **Fallback seguro:** Se o LLM falhar (timeout, erro de API), o sistema preserva o conteúdo original do executor sem sobrescrever com vazio.
- **Metadados:** Cada manifest de stage inclui `output.llm.enabled` e `output.llm.model` para auditoria.

**Exemplo de .env completo:**

```bash
# LLM Provider
KIMI_API_KEY=sk-...
KIMI_MODEL=kimi-for-coding
KIMI_BASE_URL=https://api.kimi.com/coding/v1

# VM Web App
VM_WORKSPACE_ROOT=runtime/vm
VM_DB_PATH=runtime/vm/workspace.sqlite3
```

## Bateria de Testes Pre-Release

Script unificado para validação completa antes de releases. Executa testes em estágios com falha rápida e gera evidências.

### Uso

```bash
# Listar estágios disponíveis
bash scripts/test_battery_prerelease.sh --list

# Executar estágio específico
bash scripts/test_battery_prerelease.sh --stage gate-critico

# Executar pipeline completa
bash scripts/test_battery_prerelease.sh

# Executar range de estágios
bash scripts/test_battery_prerelease.sh --from preflight --to e2e-startup

# Simular execução (dry-run)
bash scripts/test_battery_prerelease.sh --dry-run --stage gate-critico

# Salvar artefatos em diretório específico
bash scripts/test_battery_prerelease.sh --artifacts-dir /path/to/artifacts
```

### Estágios

| Estágio | Descrição | Comando executado |
|---------|-----------|-------------------|
| `preflight` | Verificações de ambiente | python3 --version, uv --version |
| `gate-critico` | Testes críticos de backend | pytest test_vm_webapp_health_probes.py |
| `backend-full` | Suite completa backend | pytest 09-tools/tests |
| `frontend-full` | Suite completa frontend | npm test -- --run (vm-ui) |
| `e2e-startup` | Testes E2E de inicialização | pytest test_vm_webapp_startup_validation.py |
| `evidence` | Geração de evidências | Coleta logs e summary |

### Interpretação de Resultados

**Arquivos gerados** (em `artifacts/test-battery/<timestamp>/`):
- `summary.txt` — Resumo da execução com status e duração
- `<stage>.log` — Log detalhado de cada estágio

**Regras de Aprovação:**
- Exit code `0` = APROVADO ✓ (todos os estágios passaram)
- Exit code `1` = BLOQUEADO ✗ (falha em pelo menos um estágio crítico)

**Exemplo de summary.txt:**
```
================================================================================
PRERELEASE BATTERY TEST SUMMARY
================================================================================
Generated: 2026-03-04 06:55:02
Working Directory: /Users/jhonatan/Repos/marketing-skills
Dry Run: false

EXECUTION SUMMARY
-----------------
Total Duration: 45s
Exit Code: 0
Result: APPROVED

STAGE LOGS
----------
- preflight.log
- gate-critico.log
- backend-full.log
- frontend-full.log
- e2e-startup.log
- evidence.log

================================================================================
```

### Política de Bloqueio

- Falha no `gate-critico` interrompe imediatamente a pipeline
- Falha em qualquer estágio após o gate loga o erro e interrompe a execução
- Artefatos são sempre gerados, mesmo em caso de falha
