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
SUMMARY_FILE=""

# Arrays para tracking
STAGE_RESULTS=()
STAGE_TIMES=()

# Funções auxiliares
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    
    # Também escreve no summary se disponível
    if [[ -n "$SUMMARY_FILE" && -f "$SUMMARY_FILE" ]]; then
        echo "$*" >> "$SUMMARY_FILE"
    fi
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
    
    # Também escreve no summary se disponível
    if [[ -n "$SUMMARY_FILE" && -f "$SUMMARY_FILE" ]]; then
        echo "ERROR: $*" >> "$SUMMARY_FILE"
    fi
}

log_stage() {
    local stage="$1"
    local message="$2"
    local stage_log="$ARTIFACTS_DIR/${stage}.log"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" >> "$stage_log"
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

# Inicializa o diretório de artefatos
init_artifacts() {
    # Criar diretório de artefatos se especificado ou usar default
    if [[ -z "$ARTIFACTS_DIR" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            # Em dry-run sem dir especificado, não criar artefatos
            return 0
        fi
        ARTIFACTS_DIR="${REPO_ROOT}/artifacts/test-battery/$(date +%Y%m%d_%H%M%S)"
    fi
    
    mkdir -p "$ARTIFACTS_DIR"
    
    if [[ "$DRY_RUN" == false ]]; then
        log "Artefatos serão salvos em: $ARTIFACTS_DIR"
        
        # Inicializar arquivos de log por estágio
        for s in "${STAGES[@]}"; do
            touch "$ARTIFACTS_DIR/${s}.log"
        done
    fi
    
    # Inicializar summary (sempre, se diretório especificado)
    SUMMARY_FILE="$ARTIFACTS_DIR/summary.txt"
    cat > "$SUMMARY_FILE" <<EOF
================================================================================
PRERELEASE BATTERY TEST SUMMARY
================================================================================
Generated: $(date '+%Y-%m-%d %H:%M:%S')
Working Directory: $REPO_ROOT
Dry Run: $DRY_RUN

PIPELINE CONFIGURATION
----------------------
EOF
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
    log_stage "$stage" "CMD: ${cmd[*]}"
    
    if "${cmd[@]}" 2>&1 | tee -a "$ARTIFACTS_DIR/${stage}.log"; then
        log_stage "$stage" "RESULT: SUCCESS"
        return 0
    else
        log_stage "$stage" "RESULT: FAILURE"
        return 1
    fi
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
    
    log "Evidence stage - artefatos já coletados nos estágios anteriores"
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

# Gera o resumo final
generate_summary() {
    local duration="$1"
    local exit_code="$2"
    local failed_stage="$3"
    
    if [[ "$DRY_RUN" == true && -n "$ARTIFACTS_DIR" && -f "$SUMMARY_FILE" ]]; then
        cat >> "$SUMMARY_FILE" <<EOF

EXECUTION SUMMARY
-----------------
Total Duration: ${duration}s
Exit Code: $exit_code
Result: $(if [[ $exit_code -eq 0 ]]; then echo "APPROVED"; else echo "BLOCKED"; fi)
EOF
        if [[ -n "$failed_stage" ]]; then
            echo "Failed Stage: $failed_stage" >> "$SUMMARY_FILE"
        fi
        
        cat >> "$SUMMARY_FILE" <<EOF

STAGE LOGS
----------
$(for s in "${STAGES[@]}"; do
    if [[ -f "$ARTIFACTS_DIR/${s}.log" ]]; then
        echo "- ${s}.log"
    fi
done)

================================================================================
EOF
    fi
    
    if [[ "$DRY_RUN" == false && -n "$SUMMARY_FILE" ]]; then
        cat >> "$SUMMARY_FILE" <<EOF

EXECUTION SUMMARY
-----------------
Total Duration: ${duration}s
Exit Code: $exit_code
Result: $(if [[ $exit_code -eq 0 ]]; then echo "APPROVED"; else echo "BLOCKED"; fi)
EOF
        if [[ -n "$failed_stage" ]]; then
            echo "Failed Stage: $failed_stage" >> "$SUMMARY_FILE"
        fi
        
        cat >> "$SUMMARY_FILE" <<EOF

STAGE LOGS
----------
$(for s in "${STAGES[@]}"; do
    if [[ -f "$ARTIFACTS_DIR/${s}.log" ]]; then
        echo "- ${s}.log"
    fi
done)

================================================================================
EOF
    fi
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

# Inicializar artefatos
init_artifacts

# Modo: estágio único
if [[ -n "$STAGE" ]]; then
    log "Executando estágio único: $STAGE"
    
    if ! run_stage "$STAGE"; then
        error "Estágio $STAGE falhou."
        exit 1
    fi
    
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

# Gerar summary
generate_summary "$DURATION" "$EXIT_CODE" "$FAILED_STAGE"

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
