# CI Weekly Health Reports

Diretório para relatórios semanais de saúde da CI.

## Gerando Relatórios

```bash
# Relatório em Markdown (padrão)
./scripts/ci_weekly_health_report.sh --branch main --limit 30

# Relatório em JSON
./scripts/ci_weekly_health_report.sh --format json --limit 50 > docs/ci/weekly-health/report-$(date +%Y%m%d).json

# Salvar relatório Markdown
./scripts/ci_weekly_health_report.sh --limit 100 > docs/ci/weekly-health/report-$(date +%Y%m%d).md
```

## Estrutura do Relatório

Cada relatório inclui:
- **Resumo por Workflow:** Total, sucessos, falhas, taxa de verde
- **Top Falhas:** Workflows com mais falhas
- **Recomendações:** Ações baseadas nos dados

## Agendamento

Recomendado: Executar toda segunda-feira:

```bash
# Cron job exemplo
0 9 * * 1 cd /path/to/repo && ./scripts/ci_weekly_health_report.sh --limit 50 > docs/ci/weekly-health/report-$(date +\%Y\%m\%d).md
```

## Histórico

| Data | Arquivo | Taxa Verde Main |
|------|---------|-----------------|
| 2026-03-04 | baseline | 0% vm-webapp-smoke |

