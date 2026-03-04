# Design: saneamento do repositorio antes da bateria de debug

## Contexto
O repositorio entrou em estado de ruido alto no `git status` por arquivos de ambiente virtual versionados no passado (`.venv` e `09-tools/.venv`).
A meta desta etapa e deixar o repositrio limpo e previsivel antes de iniciar uma bateria de debug ampla.

## Decisoes aprovadas
- Escopo: aplicar limpeza definitiva (opcao 1) para remover `.venv` e `09-tools/.venv` do versionamento sem apagar arquivos locais.
- `uv.lock`: manter sincronizado com `pyproject.toml`.
- `docs/kimi/`: manter fora do commit principal de saneamento.

## Arquitetura e escopo
- Objetivo A: eliminar ruido cronico de controle de versao.
- Objetivo B: consolidar lockfile valido para reproduzibilidade.
- Objetivo C: separar higiene de repositorio da bateria de debug funcional.

## Fluxo de execucao
1. Capturar baseline (`git status`, diff de lockfile).
2. Remover `.venv` e `09-tools/.venv` apenas do indice (`git rm --cached`).
3. Garantir `.gitignore` explicito para ambientes virtuais.
4. Manter `uv.lock` atualizado.
5. Validar com smoke checks rapidos (import/teste curto).
6. Entregar com commit de higiene.

## Riscos e mitigacao
- Remocao indevida de paths: revisar `git diff --cached --name-status` antes de commit.
- Divergencia de lockfile: validar com comando de execucao em `uv`.
- Escopo poluido por docs auxiliares: excluir `docs/kimi/` deste commit.

## Rollback
- Antes do commit: `git restore --staged <path>`.
- Depois do commit: `git revert <hash>`.

## Criterios de aceite
- `git status` sem avalanche de `.venv`.
- `.venv` e `09-tools/.venv` nao rastreados pelo Git.
- `uv.lock` coerente com `pyproject.toml`.
- Smoke check rapido sem regressao.
