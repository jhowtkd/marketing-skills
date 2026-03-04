#!/usr/bin/env bash
# CI Weekly Health Report Generator
# Gera relatório semanal de saúde da branch main

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Configurações padrão
BRANCH="main"
LIMIT=30
OUTPUT_FORMAT="markdown"

# Cores para terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

CI Weekly Health Report - Gera relatório de saúde da CI

Options:
    --branch BRANCH     Branch a analisar (default: main)
    --limit N           Número de runs a analisar (default: 30)
    --format FORMAT     Formato de saída: markdown, json (default: markdown)
    --help              Mostra esta ajuda

Examples:
    $(basename "$0") --branch main --limit 50
    $(basename "$0") --format json --limit 100 > report.json
EOF
}

# Parse argumentos
while [[ $# -gt 0 ]]; do
    case "$1" in
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --limit)
            LIMIT="$2"
            shift 2
            ;;
        --format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Opção desconhecida: $1" >&2
            usage
            exit 1
            ;;
    esac
done

# Verifica dependências
if ! command -v gh &> /dev/null; then
    echo "Erro: GitHub CLI (gh) não encontrado" >&2
    exit 1
fi

# Gera relatório em Markdown
generate_markdown() {
    local branch="$1"
    local limit="$2"
    
    echo "# CI Weekly Health Report"
    echo ""
    echo "**Branch:** \`$branch\`  "
    echo "**Data:** $(date '+%Y-%m-%d %H:%M:%S')  "
    echo "**Período:** Últimos $limit runs"
    echo ""
    echo "---"
    echo ""
    
    # Coleta dados
    echo "## 📊 Resumo por Workflow"
    echo ""
    echo "| Workflow | Total | Sucessos | Falhas | Taxa Verde |"
    echo "|----------|-------|----------|--------|------------|"
    
    gh run list --branch "$branch" --limit "$limit" --json workflowName,conclusion \
        --jq 'group_by(.workflowName) | map({workflow: .[0].workflowName, total: length, success: map(select(.conclusion == "success")) | length}) | sort_by(-.total) | .[] | "| \(.workflow) | \(.total) | \(.success) | \(.total - .success) | \((.success / .total * 100) | floor)% |"' 2>/dev/null || echo "| Erro ao coletar dados | - | - | - | - |"
    
    echo ""
    echo "## 🔴 Top Falhas"
    echo ""
    echo "| Workflow | Falhas | % do Total |"
    echo "|----------|--------|------------|"
    
    gh run list --branch "$branch" --limit "$limit" --json workflowName,conclusion \
        --jq 'group_by(.workflowName) | map({workflow: .[0].workflowName, total: length, failures: map(select(.conclusion == "failure")) | length}) | sort_by(-.failures) | .[0:5] | .[] | select(.failures > 0) | "| \(.workflow) | \(.failures) | \((.failures / .total * 100) | floor)% |"' 2>/dev/null || echo "| Erro ao coletar dados | - | - |"
    
    echo ""
    echo "## ⏱️ Tempo Médio de Execução"
    echo ""
    echo "_Dado não disponível via gh CLI sem acesso a logs detalhados_"
    echo ""
    echo "## 📋 Recomendações"
    echo ""
    
    # Identifica workflows críticos
    local critical_failures
    critical_failures=$(gh run list --branch "$branch" --limit "$limit" --json workflowName,conclusion \
        --jq '[group_by(.workflowName) | map({workflow: .[0].workflowName, total: length, failures: map(select(.conclusion == "failure")) | length, rate: (map(select(.conclusion == "success")) | length) / length}) | select(.rate < 0.5 and .total > 5)] | length' 2>/dev/null || echo "0")
    
    if [[ "$critical_failures" -gt 0 ]]; then
        echo "- ⚠️ **$critical_failures workflows** com taxa de verde < 50% - Priorizar correção"
    fi
    
    echo "- 📊 Review semanal de gates marcados como \`legacy\` na governance matrix"
    echo "- 🎯 Meta: 80% taxa de verde na main (SLO definido)"
    echo ""
    echo "---"
    echo ""
    echo "*Relatório gerado por \`scripts/ci_weekly_health_report.sh\`*"
}

# Gera relatório em JSON
generate_json() {
    local branch="$1"
    local limit="$2"
    
    gh run list --branch "$branch" --limit "$limit" --json workflowName,conclusion,createdAt \
        --jq '{
            meta: {
                branch: "'"$branch"'",
                generated_at: "'"$(date -Iseconds)"'",
                limit: '"$limit"'
            },
            summary: (group_by(.workflowName) | map({workflow: .[0].workflowName, total: length, success: map(select(.conclusion == "success")) | length, failure: map(select(.conclusion == "failure")) | length, success_rate: ((map(select(.conclusion == "success")) | length) / length * 100) | floor}) | sort_by(-.total)),
            top_failures: (group_by(.workflowName) | map({workflow: .[0].workflowName, failures: map(select(.conclusion == "failure")) | length}) | sort_by(-.failures) | .[0:5])
        }' 2>/dev/null || echo '{"error": "Failed to fetch data"}'
}

# Main
case "$OUTPUT_FORMAT" in
    markdown)
        generate_markdown "$BRANCH" "$LIMIT"
        ;;
    json)
        generate_json "$BRANCH" "$LIMIT"
        ;;
    *)
        echo "Formato desconhecido: $OUTPUT_FORMAT" >&2
        exit 1
        ;;
esac
