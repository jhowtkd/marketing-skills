# VM Studio Quality Compare + Guided Regeneration Design

## Status
Proposta aprovada para implementacao.

---

## 1. Objetivo

Entregar o proximo slice do VM Studio `deliverable-first` com tres capacidades de produto:

- comparacao entre versoes (`scorecard + diff`)
- score de qualidade hibrido (`heuristico local + avaliacao profunda opcional por LLM`)
- regeneracao guiada (`presets + prompt assistido no mesmo modal`)

O resultado esperado e melhorar decisao editorial, acelerar iteracao e reduzir retrabalho na entrega final.

---

## 2. Escopo Validado

Decisoes validadas:

- abordagem: `Progressive hybrid`
- score: `hibrido`
- comparacao: `scorecard no topo + diff abaixo`
- regeneracao guiada: `presets + campo assistido`

Regras de escopo:

- o fluxo principal permanece no frontend React atual (`09-tools/web/vm-ui/src`)
- backend atual segue funcionando sem breaking changes
- avaliacao profunda e opcional e resiliente (falha nao bloqueia uso)

---

## 3. Problema Atual

Depois do redesign `deliverable-first`, o usuario consegue gerar, aprovar e baixar entregaveis com clareza. Ainda faltam mecanismos para decidir rapidamente:

- qual versao esta melhor e por que
- se a qualidade esta aceitavel para entrega
- como melhorar a versao sem escrever prompt do zero

Sem isso, a iteracao continua manual e subjetiva.

---

## 4. Abordagens Consideradas

## 4.1 UI-first (somente frontend)

Descricao:

- score local basico
- comparacao visual
- regeneracao guiada sem avaliacao LLM

Pros:

- entrega rapida
- menor risco tecnico

Contras:

- avaliacao semantica limitada
- menor confianca para decisoes finais

## 4.2 Quality-first (motor primeiro)

Descricao:

- construir motor de avaliacao completo (local + LLM) antes da UI

Pros:

- base forte de qualidade

Contras:

- pouco valor visivel no curto prazo
- atraso no ganho de UX

## 4.3 Progressive hybrid (escolhida)

Descricao:

- MVP ja traz UI completa de comparacao/regeneracao
- score local sempre disponivel
- botao `Avaliar profundo` chama LLM on-demand

Pros:

- valor imediato + base evolutiva
- custo de LLM sob controle
- fallback robusto

Contras:

- exige coordenacao frontend/backend

---

## 5. Solucao Proposta

## 5.1 Visao de Produto

Novo bloco no canvas da versao ativa:

- `Qualidade`:
  - score local (0-100)
  - badges de criterio
  - recomendacao curta
- `Comparar versoes`:
  - seletor de versao base e versao alvo
  - scorecard comparativo
  - diff textual
- `Regeneracao guiada`:
  - presets de melhoria
  - campo assistido de instrucao adicional
  - CTA `Regenerar com guia`

## 5.2 Score Hibrido

### Camada 1: Heuristico local (sincrono)

Entrada:

- markdown da versao ativa
- metadados basicos de run

Saida:

- `overall_score`
- sub-scores por criterio:
  - completude
  - estrutura
  - clareza
  - CTA
  - acionabilidade
- alertas e recomendacoes

Criticos tecnicos:

- calculo deterministico e barato
- sempre disponivel
- sem dependencia de rede

### Camada 2: Avaliacao profunda (assinc, opcional)

Entrada:

- artefato atual
- contexto da versao
- rubric de avaliacao

Saida:

- score semantico refinado
- justificativa curta por criterio
- recomendacoes priorizadas

Regras:

- acionada apenas quando usuario clicar
- timeout curto + fallback para heuristico
- nunca bloqueia comparacao/regeneracao

---

## 6. Comparacao de Versoes

Layout da secao:

- topo: scorecard comparativo lado a lado
  - versao A vs versao B
  - delta por criterio
  - destaque de vencedor por criterio
- abaixo: diff textual do markdown
  - adicoes, remocoes, alteracoes
  - foco em legibilidade, nao raw patch tecnico

Comportamento:

- default compara `versao ativa` com `versao anterior`
- usuario pode trocar versao base/alvo
- quando nao houver versao anterior, mostrar estado vazio orientado

---

## 7. Regeneracao Guiada

Modal unico com dois blocos:

- presets (multi-select):
  - `Mais profundo`
  - `Mais direto`
  - `Mais persuasivo`
  - `Mais orientado a conversao`
  - `Mais tecnico`
  - `Mais simples`
- prompt assistido:
  - campo livre
  - sugestoes automáticas baseadas no score

Payload final de regeneracao:

- request_text base da versao
- instrucoes dos presets selecionados
- complemento do usuario
- opcional: pontos fracos detectados

Regra de UX:

- mostrar preview do "guia aplicado" antes de confirmar
- criar nova versao (nunca sobrescrever antiga)

---

## 8. Arquitetura Tecnica

## 8.1 Frontend

Arquivos-alvo principais:

- [WorkspacePanel.tsx](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx)
- [useWorkspace.ts](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/features/workspace/useWorkspace.ts)
- [presentation.ts](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/features/workspace/presentation.ts)
- [ArtifactPreview.tsx](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/features/inbox/ArtifactPreview.tsx)

Novos modulos sugeridos:

- `src/features/quality/score.ts` (heuristica local)
- `src/features/quality/types.ts`
- `src/features/quality/VersionComparisonPanel.tsx`
- `src/features/quality/GuidedRegenerateModal.tsx`
- `src/features/quality/diff.ts`

## 8.2 Backend (opcional para deep eval)

Arquivo-alvo:

- [api.py](/Users/jhonatan/Repos/marketing-skills/09-tools/vm_webapp/api.py)

Novo endpoint opcional:

- `POST /api/v2/workflow-runs/{run_id}/quality-evaluation`

Contrato minimo:

- request: `rubric_version`, `depth` (`quick|deep`)
- response: score detalhado + recomendacoes
- falhas retornam erro amigavel sem quebrar frontend

---

## 9. Fluxo de Dados

1. usuario seleciona versao ativa
2. frontend calcula score heuristico local
3. frontend exibe scorecard e diff com versao de referencia
4. usuario opcionalmente clica `Avaliar profundo`
5. frontend chama endpoint de avaliacao
6. resultado profundo atualiza scorecard com badge `Deep`
7. usuario abre `Regeneracao guiada`
8. frontend cria nova run com request guiado

---

## 10. Estados e Erros

Estados obrigatorios:

- sem versao suficiente para comparar
- calculando score local
- avaliacao profunda em progresso
- avaliacao profunda indisponivel (fallback ativo)
- regeneracao enviada

Politica de erro:

- erro de deep eval nao derruba tela
- exibir mensagem curta + manter score local
- detalhes tecnicos apenas em `Dev mode`

---

## 11. Testes

Cobertura minima:

- score heuristico com casos positivos/negativos
- scorecard comparativo com delta correto
- diff renderizando adicao/remocao/alteracao
- modal de regeneracao montando payload correto
- fallback quando deep eval falha

Suites:

- Vitest unit tests para qualidade/diff/payload
- testes de componentes React para painel/modal
- smoke manual no Studio real

---

## 12. Criterios de Sucesso

- usuario identifica rapidamente qual versao esta melhor
- score local aparece de forma confiavel em todas as versoes
- avaliacao profunda opcional funciona sem bloquear fluxo
- regeneracao guiada reduz tempo para chegar em versao final
- nenhum impacto negativo no fluxo atual de gerar/aprovar/baixar
