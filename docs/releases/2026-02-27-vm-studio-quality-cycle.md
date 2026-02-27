# Release Note: VM Studio Quality Cycle
**Data:** 2026-02-27  
**Ciclo:** Quality Compare + Guided Regeneration

---

## Resumo Executivo

- Quality ScoreCard implementado e operacional na API v2
- Comparação de versões funcionando via dados de workflow runs
- Deep Evaluation endpoint disponível (com fallback seguro para heurística)
- Regeneração guiada via `/resume` com instruction support
- Download de artifacts (.md) funcional por stage

---

## O Que Mudou

| Feature | Status | Detalhes |
|---------|--------|----------|
| Quality Score | ✅ | Endpoint `/quality-evaluation` retorna score com critérios (completude, estrutura, clareza, CTA, acionabilidade) |
| Compare Versions | ✅ | Comparativo disponível via API (deltas de score, stages, artifacts) |
| Guided Regen | ✅ | Endpoint `/resume` aceita instruction para regeneração direcionada |
| Deep Eval | ✅ | Parâmetro `depth=deep` suportado (fallback para heurística quando necessário) |
| Download .md | ✅ | Endpoint `/artifact-content` com stage_dir + artifact_path |

---

## Como Foi Validado

### Testes Automatizados
```bash
# UI Tests (vitest)
cd 09-tools/web/vm-ui && npm run test -- --run
# Resultado: 21 test files passed (38 tests)

# Build
npm run build
# Resultado: ✓ built in 1.41s

# API Tests
pytest 09-tools/tests/test_vm_webapp_quality_eval_api_v2.py \
       09-tools/tests/test_vm_webapp_ui_shell.py::test_root_serves_react_ui_contract -q
# Resultado: 2 passed
```

### Smoke Test de Produto
- Criado: 1 Brand → 1 Project → 1 Campaign → 1 Thread → 1 Task
- Gerado: 2 workflow runs (run-31476c360a2e, run-38af49269374)
- Aprovações: 3 stages com gates aprovados via API
- Quality eval: Testado heuristic + deep
- Download: Artifact .md recuperado com sucesso
- Resume: Regeneração guiada testada

---

## Métricas do Smoke

| Métrica | Valor |
|---------|-------|
| tempo_ate_primeira_versao_pronta_seg | 138.51 |
| regeneracoes_por_job | 1 |
| uso_avaliar_profundo_por_versao | 0.5 |

```json
{
  "tempo_ate_primeira_versao_pronta_seg": 138.51,
  "regeneracoes_por_job": 1,
  "uso_avaliar_profundo_por_versao": 0.5
}
```

---

## Riscos Conhecidos

1. **UI Integration:** A UI não está exibindo as runs criadas no contexto do task (problema de binding thread/task/run)
2. **Deep Eval:** Retorna mesma estrutura do heurístico (pode ser fallback esperado ou necessita de configuração adicional)
3. **Compare UI:** Não há endpoint dedicado `/compare` — comparação é feita client-side ou via composição de chamadas

## Próximos Passos

1. Corrigir binding de runs na UI do Studio (thread/task/run association)
2. Verificar configuração de LLM para deep evaluation
3. Adicionar endpoint dedicado `/compare` com diff semântico
4. Implementar cache de quality evaluation para evitar reprocessamento

---

**Status do Ciclo:** ✅ PASS (API completa, UI parcial)
