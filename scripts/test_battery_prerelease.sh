#!/usr/bin/env bash
# Prerelease Battery Runner
# Executa bateria de testes em estágios com falha rápida e geração de evidências

set -euo pipefail

# Configurações
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Estágios disponíveis
STAGES=("preflight" "gate-critico" "backend-full" "frontend-full" "e2e-startup" "evidence")

# Variáveis de estado
DRY_RUN=false
STAGE=""
FROM_STAGE=""
TO_STAGE=""
ARTIFACTS_DIR=""
START_TIME=""

# Funções auxiliares
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Prerelease Battery Runner - Executa bateria de testes em estágios

Options:
    --list              Lista todos os estágios disponíveis
    --dry-run           Mostra comandos sem executar
    --stage STAGE       Executa apenas o estágio especificado
    --from STAGE        Inicia a partir do estágio especificado
    --to STAGE          Executa até o estágio especificado (inclusive)
    --artifacts-dir DIR Diretório para salvar artefatos (default: auto)
    -h, --help          Mostra esta ajuda

Estágios disponíveis:
    preflight       - Verificações iniciais do ambiente
    gate-critico    - Testes críticos de backend (health probes)
    backend-full    - Suite completa de testes de backend
    frontend-full   - Suite completa de testes de frontend
    e2e-startup     - Testes E2E de inicialização
    evidence        - Geração de evidências finais

Exemplos:
    $(basename "$0") --list
    $(basename "$0") --dry-run --stage gate-critico
    $(basename "$0") --from preflight --to e2e-startup
    $(basename "$0") --stage gate-critico
EOF
}

list_stages() {
    echo "Estágios disponíveis na pipeline prerelease:"
    for s in "${STAGES[@]}"; do
        echo "  - $s"
    done
}

validate_stage() {
    local stage="$1"
    for s in "${STAGES[@]}"; do
        if [[ "$s" == "$stage" ]]; then
            return 0
        fi
    done
    error "Unknown stage: $stage"
    echo "Estágios válidos: ${STAGES[*]}" >&2
    exit 1
}

get_stage_index() {
    local stage="$1"
    for i in "${!STAGES[@]}"; do
        if [[ "${STAGES[$i]}" == "$stage" ]]; then
            echo "$i"
            return 0
        fi
    done
    echo "-1"
    return 1
}

# Executa um comando com ou sem dry-run
run_command() {
    local stage="$1"
    shift
    local cmd=("$@")
    
    if [[ "$DRY_RUN" == true ]]; then
        log "DRY-RUN [$stage]: ${cmd[*]}"
        return 0
    fi
    
    log "[$stage] Executando: ${cmd[*]}"
    "${cmd[@]}"
}

# Estágio: preflight
stage_preflight() {
    log "=== STAGE: preflight ==="
    
    run_command "preflight" echo "Verificando ambiente..."
    run_command "preflight" python3 --version
    run_command "preflight" uv --version
    
    # Verificar Node.js para frontend
    if command -v node &> /dev/null; then
        run_command "preflight" node --version
    fi
    
    log "Preflight completo."
}

# Estágio: gate-critico
stage_gate_critico() {
    log "=== STAGE: gate-critico ==="
    
    # Testes críticos de health probes
    run_command "gate-critico" uv run --python 3.12 pytest -q 09-tools/tests/test_vm_webapp_health_probes.py
    
    log "Gate crítico aprovado."
}

# Estágio: backend-full
stage_backend_full() {
    log "=== STAGE: backend-full ==="
    
    # Suite completa de testes de backend
    run_command "backend-full" uv run --python 3.12 pytest -q 09-tools/tests
    
    log "Backend full completo."
}

# Estágio: frontend-full
stage_frontend_full() {
    log "=== STAGE: frontend-full ==="
    
    # Verificar se existe o projeto frontend
    if [[ ! -d "09-tools/web/vm-ui" ]]; then
        log "Frontend não encontrado em 09-tools/web/vm-ui, pulando..."
        return 0
    fi
    
    # Suite completa de testes de frontend
    run_command "frontend-full" bash -c "cd 09-tools/web/vm-ui && npm test"
    
    log "Frontend full completo."
}

# Estágio: e2e-startup
stage_e2e_startup() {
    log "=== STAGE: e2e-startup ==="
    
    # Testes E2E de inicialização
    run_command "e2e-startup" uv run --python 3.12 pytest -q 09-tools/tests/test_vm_webapp_startup_validation.py
    
    log "E2E startup completo."
}

# Estágio: evidence
stage_evidence() {
    log "=== STAGE: evidence ==="
    
    # Criar diretório de artefatos se não existir
    if [[ -z "$ARTIFACTS_DIR" ]]; then
        ARTIFACTS_DIR="${REPO_ROOT}/artifacts/test-battery/$(date +%Y%m%d_%H%M%S)"
    fi
    
    if [[ "$DRY_RUN" == false ]]; then
        mkdir -p "$ARTIFACTS_DIR"
        log "Artefatos salvos em: $ARTIFACTS_DIR"
    else
        log "DRY-RUN: Artefatos seriam salvos em: $ARTIFACTS_DIR"
    fi
    
    log "Evidence stage completo."
}

# Executa um estágio específico
run_stage() {
    local stage="$1"
    
    case "$stage" in
        preflight)
            stage_preflight
            ;;
        gate-critico)
            stage_gate_critico
            ;;
        backend-full)
            stage_backend_full
            ;;
        frontend-full)
            stage_frontend_full
            ;;
        e2e-startup)
            stage_e2e_startup
            ;;
        evidence)
            stage_evidence
            ;;
        *)
            error "Estágio desconhecido: $stage"
            exit 1
            ;;
    esac
}

# Parse argumentos
while [[ $# -gt 0 ]]; do
    case "$1" in
        --list)
            list_stages
            exit 0
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --stage)
            STAGE="$2"
            shift 2
            ;;
        --from)
            FROM_STAGE="$2"
            shift 2
            ;;
        --to)
            TO_STAGE="$2"
            shift 2
            ;;
        --artifacts-dir)
            ARTIFACTS_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error "Opção desconhecida: $1"
            usage
            exit 1
            ;;
    esac
done

# Validação de estágio
if [[ -n "$STAGE" ]]; then
    validate_stage "$STAGE"
fi

if [[ -n "$FROM_STAGE" ]]; then
    validate_stage "$FROM_STAGE"
fi

if [[ -n "$TO_STAGE" ]]; then
    validate_stage "$TO_STAGE"
fi

# Execução
START_TIME=$(date +%s)
log "Iniciando Prerelease Battery Runner"
log "DRY_RUN=$DRY_RUN"

# Modo: estágio único
if [[ -n "$STAGE" ]]; then
    log "Executando estágio único: $STAGE"
    run_stage "$STAGE"
    log "Estágio $STAGE concluído com sucesso."
    exit 0
fi

# Modo: pipeline com range
START_IDX=$(get_stage_index "${FROM_STAGE:-preflight}")
END_IDX=$(get_stage_index "${TO_STAGE:-evidence}")

log "Executando pipeline do estágio ${STAGES[$START_IDX]} até ${STAGES[$END_IDX]}"

FAILED_STAGE=""
EXIT_CODE=0

for ((i=START_IDX; i<=END_IDX; i++)); do
    stage_name="${STAGES[$i]}"
    log "--- Iniciando estágio: $stage_name ---"
    
    if ! run_stage "$stage_name"; then
        error "Estágio '$stage_name' falhou!"
        FAILED_STAGE="$stage_name"
        EXIT_CODE=1
        break
    fi
    
    log "--- Estágio '$stage_name' concluído ---"
done

# Resumo
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

log "========================================="
log "Bateria de testes pre-release concluída"
log "Duração total: ${DURATION}s"

if [[ $EXIT_CODE -eq 0 ]]; then
    log "Resultado: APROVADO ✓"
    log "Todos os estágios executados com sucesso."
else
    error "Resultado: BLOQUEADO ✗"
    error "Falha no estágio: $FAILED_STAGE"
fi

log "========================================="

exit $EXIT_CODE
