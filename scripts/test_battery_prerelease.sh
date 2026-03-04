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

# Se solicitado dry-run de um estágio específico
if [[ "$DRY_RUN" == true && -n "$STAGE" ]]; then
    log "DRY-RUN: Simulando execução do estágio '$STAGE'"
    
    case "$STAGE" in
        gate-critico)
            echo "DRY-RUN: uv run --python 3.12 pytest -q 09-tools/tests/test_vm_webapp_health_probes.py"
            ;;
        backend-full)
            echo "DRY-RUN: uv run --python 3.12 pytest -q 09-tools/tests"
            ;;
        frontend-full)
            echo "DRY-RUN: cd 09-tools/web/vm-ui && npm test"
            ;;
        *)
            echo "DRY-RUN: Comandos para estágio '$STAGE'"
            ;;
    esac
    
    exit 0
fi

# Se solicitado dry-run sem estágio específico (pipeline completa)
if [[ "$DRY_RUN" == true && -z "$STAGE" ]]; then
    log "DRY-RUN: Simulando execução completa da pipeline"
    
    # Determinar range de estágios
    local_start=0
    local_end=$((${#STAGES[@]} - 1))
    
    if [[ -n "$FROM_STAGE" ]]; then
        for i in "${!STAGES[@]}"; do
            if [[ "${STAGES[$i]}" == "$FROM_STAGE" ]]; then
                local_start=$i
                break
            fi
        done
    fi
    
    if [[ -n "$TO_STAGE" ]]; then
        for i in "${!STAGES[@]}"; do
            if [[ "${STAGES[$i]}" == "$TO_STAGE" ]]; then
                local_end=$i
                break
            fi
        done
    fi
    
    for ((i=local_start; i<=local_end; i++)); do
        echo "DRY-RUN: [${STAGES[$i]}]"
    done
    
    exit 0
fi

# Execução real (placeholder para implementação futura)
log "Prerelease Battery Runner"
log "DRY_RUN=$DRY_RUN, STAGE=$STAGE"
log "Implementação completa em desenvolvimento..."

exit 0
