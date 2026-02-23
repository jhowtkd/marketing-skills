# Design: `@vm-onboard` para MCP + IDE Onboarding (V1)

**Data:** 2026-02-23  
**Projeto:** `/Users/jhonatan/Repos/Projeto mkt/mkt-hibrido/vibe-marketing-skill`  
**Status:** Aprovado em brainstorming

## 1. Objetivo

Adicionar um comando de onboarding no pacote (`@vm-onboard`) para configurar MCPs e integração de IDEs de forma guiada, segura e reproduzível.

O fluxo deve:
- cobrir Codex, Cursor, Kimi e Antigravity;
- operar em modo híbrido (preview/diff + confirmação por IDE);
- configurar também as chaves premium (`PERPLEXITY_API_KEY`, `FIRECRAWL_API_KEY`) com confirmação explícita.

## 2. Escopo V1

- Comando oficial da skill: `@vm-onboard`.
- Entrypoint técnico: `python3 09-tools/onboard.py run`.
- IDEs cobertas:
  - Codex
  - Cursor
  - Kimi
  - Antigravity
- Política de aplicação:
  - gerar preview por IDE;
  - confirmar aplicar/pular por IDE;
  - aplicar somente itens aprovados.
- Chaves premium:
  - pedir/configurar `PERPLEXITY_API_KEY` e `FIRECRAWL_API_KEY`;
  - mostrar preview de alteração no profile shell;
  - aplicar apenas com confirmação.
- Relatório final com status por IDE e por chave.

## 3. Fora de Escopo V1

- Setup de provedores além de Perplexity/Firecrawl.
- Provisionamento remoto de segredos (vault/cloud secret manager).
- UI gráfica dedicada para onboarding.
- Suporte oficial para IDEs fora das quatro aprovadas.

## 4. Abordagem Selecionada

**Abordagem 2: Python orquestrador + adaptadores por IDE** (recomendada e aprovada).

Racional:
- melhor testabilidade;
- separação clara por IDE;
- menor risco de regressão ao adicionar novos providers/IDEs;
- suporte natural a fluxo preview/diff por item.

## 5. Arquitetura

### 5.1 Camadas

1. Skill Command Layer
- Exposição do comando `@vm-onboard`.
- Delega para o entrypoint de onboarding.

2. Onboarding Orchestrator
- `09-tools/onboard.py`.
- Coordena descoberta, preview, confirmação, aplicação e relatório.

3. IDE Adapters
- Módulos dedicados por IDE com regras próprias de path/merge/validação.

4. Secrets & Shell Layer
- Fluxo de configuração das variáveis premium no profile shell.
- Regras de atualização idempotente de `export`.

5. Audit/Report Layer
- Sumário final consolidado para rápida leitura e troubleshooting.

### 5.2 Componentes

Arquivos novos:
- `09-tools/onboard.py`
- `09-tools/onboard_report.py`
- `09-tools/onboard_adapters/__init__.py`
- `09-tools/onboard_adapters/base.py`
- `09-tools/onboard_adapters/codex.py`
- `09-tools/onboard_adapters/cursor.py`
- `09-tools/onboard_adapters/kimi.py`
- `09-tools/onboard_adapters/antigravity.py`

Arquivos alterados:
- `09-tools/setup.sh` (integração orientada ao onboarding)
- `README.md`
- `00-orchestrator/orchestrator.md`

## 6. Contratos

### 6.1 CLI Interna

Comando:
- `python3 09-tools/onboard.py run`

Flags:
- `--ide codex,cursor,kimi,antigravity` (opcional)
- `--dry-run`
- `--yes` (auto-apply)
- `--shell-file <path>`

Saída:
- preview/diff por IDE;
- decisão aplicada por IDE (`applied`/`skipped`/`manual_required`/`failed`);
- resumo de chaves e próximos passos.

### 6.2 Comando da Skill

Comando oficial:
- `@vm-onboard`

Comportamento:
- dispara fluxo de onboarding end-to-end;
- inclui etapa de chaves premium no mesmo comando.

### 6.3 Regras de Escrita

- Nunca sobrescrever arquivo de config sem preview.
- Backup antes da aplicação.
- Merge conservador com idempotência.
- Em arquivo inválido/desconhecido: marcar `manual_required`.

## 7. Fluxo Operacional

1. Descobrir IDEs e paths.
2. Construir plano de mudanças por IDE.
3. Exibir preview/diff por IDE.
4. Confirmar `apply/skip` por IDE.
5. Aplicar mudanças aprovadas com backup.
6. Coletar e configurar chaves premium com preview/confirm.
7. Validar pós-aplicação.
8. Emitir relatório final.

## 8. Erros, Recuperação e Idempotência

- Falha por IDE não interrompe onboarding das demais IDEs.
- Falha na configuração de chave não invalida configurações já aplicadas.
- Reexecução não duplica blocos de config nem exports.
- Backup timestampado habilita rollback manual.

## 9. Critérios de Aceite

Aceite funcional:
- `@vm-onboard` cobre as 4 IDEs.
- Preview e confirmação por IDE funcionando.
- Configuração de chaves com confirmação explícita.
- Relatório final com status de IDEs e segredos.

Aceite técnico:
- Reexecução idempotente.
- Sem dependência de CWD para paths críticos.
- Tratamento robusto para permissões e arquivo inválido.

Aceite de testes:
- Cobertura de `dry-run`, apply parcial, apply total.
- Testes de atualização de profile sem duplicação.
- Testes de erro de permissão e recuperação.

## 10. Decisões Validadas

- Entrada híbrida e comando da skill padronizado em `@vm-onboard`.
- Cobertura inicial de Codex + Cursor + Kimi + Antigravity.
- Modo híbrido de aplicação (preview/diff + confirmação por IDE).
- Inclusão obrigatória da configuração de chaves no fluxo.

