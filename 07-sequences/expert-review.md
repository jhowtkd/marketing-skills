# 👁️ Expert Review

> Framework de revisão especializada para garantir qualidade.

---

## 🎯 O que é Expert Review?

Sistema de revisão que aplica critérios especializados para garantir que todo output atenda aos mais altos padrões.

---

## 🔬 3 Tipos de Revisão

### 1. Copy Review
**Comando:** `@vm-review-copy`

**Critérios:**
```markdown
## Copy Review Checklist

### Clareza
- [ ] Mensagem principal é óbvia em 5 segundos?
- [ ] Cada parágrafo tem um objetivo claro?
- [ ] Não há ambiguidades?

### Persuasão
- [ ] Headline tem gancho forte?
- [ ] Problema é agitado adequadamente?
- [ ] Solução é apresentada claramente?
- [ ] Provas são convincentes?
- [ ] CTA é irresistível?

### Estrutura
- [ ] Fluxo lógico (AIDA/PAS/etc)?
- [ ] Transições suaves?
- [ ] Hierarquia visual clara?

### Tom de Voz
- [ ] Alinhado com brand voice?
- [ ] Apropriado para público?
- [ ] Consistente do início ao fim?

### Gramática
- [ ] Sem erros ortográficos
- [ ] Pontuação correta
- [ ] Concisão (sem redundâncias)

### Score: ___/30
```

---

### 2. Design Review
**Comando:** `@vm-review-design`

**Critérios:**
```markdown
## Design Review Checklist

### Hierarquia Visual
- [ ] Elementos mais importantes são os mais visíveis?
- [ ] Fluxo visual claro (Z-pattern/F-pattern)?
- [ ] Contraste adequado?

### Branding
- [ ] Cores da marca aplicadas?
- [ ] Tipografia consistente?
- [ ] Logo presente (se aplicável)?

### Usabilidade
- [ ] CTA é óbvio?
- [ ] Formulários são claros?
- [ ] Navegação intuitiva?

### Mobile
- [ ] Responsivo?
- [ ] Touch-friendly?
- [ ] Legível em telas pequenas?

### Performance
- [ ] Imagens otimizadas?
- [ ] Carregamento rápido?
- [ ] Sem elementos pesados desnecessários?

### Score: ___/30
```

---

### 3. Strategy Review
**Comando:** `@vm-review-strategy`

**Critérios:**
```markdown
## Strategy Review Checklist

### Alinhamento
- [ ] Estratégia alinha com objetivos de negócio?
- [ ] Público-alvo está correto?
- [ ] Posicionamento é adequado?

### Diferenciação
- [ ] Proposta de valor é única?
- [ ] Diferencial é claro?
- [ ] Concorrência foi considerada?

### Viabilidade
- [ ] É executável?
- [ ] Recursos necessários estão claros?
- [ ] Timeline é realista?

### Mensuração
- [ ] KPIs definidos?
- [ ] Métricas de sucesso claras?
- [ ] Sistema de tracking planejado?

### Riscos
- [ ] Riscos identificados?
- [ ] Mitigações planejadas?
- [ ] Planos B considerados?

### Score: ___/30
```

---

## 🎯 Full Review
**Comando:** `@vm-review-all`

Combina os 3 reviews em um único relatório:

```markdown
# Full Expert Review
## [Nome do Projeto/Asset]

---

## Copy Review
**Score:** ___/30

### Pontos Fortes
- 
- 

### Pontos a Melhorar
- 
- 

### Recomendações
1. 
2. 

---

## Design Review
**Score:** ___/30

### Pontos Fortes
- 
- 

### Pontos a Melhorar
- 
- 

### Recomendações
1. 
2. 

---

## Strategy Review
**Score:** ___/30

### Pontos Fortes
- 
- 

### Pontos a Melhorar
- 
- 

### Recomendações
1. 
2. 

---

## Score Total: ___/90

### Interpretação
- 80-90: Excelente - Pronto para publicar
- 60-79: Bom - Pequenos ajustes necessários
- 40-59: Regular - Revisão significativa
- <40: Fraco - Refazer

### Próximos Passos
- [ ] Aplicar recomendações
- [ ] Revisar novamente
- [ ] Aprovar final
```

---

## 📋 Como Usar

### Para Copy
```
@vm-review-copy

[COLE SUA COPY AQUI]

Framework usado: [AIDA/PAS/etc]
Objetivo: [clique/cadastro/compra]
Público: [descrição]
```

### Para Design
```
@vm-review-design

[DESCREVA O DESIGN/COLE IMAGEM]

Tipo: [landing/email/ad]
Objetivo: [conversão/engajamento]
```

### Para Estratégia
```
@vm-review-strategy

[COLE SUA ESTRATÉGIA]

Contexto: [breve descrição]
Objetivo: [o que quer alcançar]
```

### Completo
```
@vm-review-all

[COLE TODOS OS MATERIAIS]

Contexto: [descrição completa]
```

---

## 💡 Dicas de Revisão

1. **Seja honesto** - A revisão é para melhorar
2. **Seja específico** - "Melhorar" não ajuda
3. **Dê exemplos** - Mostre como fazer
4. **Priorize** - O que é mais importante?
5. **Itere** - Revise, ajuste, revise de novo

---

## 🤖 Multi-Agent Expert Review (via Compound Growth OS)

Use perspectivas independentes para reduzir vieses de agente único.

### Quando Executar

Checkpoints obrigatórios:
- Após recomendação estratégica (antes de produzir assets).
- Após produção de assets (antes de publicar).
- Antes de decisões de alto risco (spend ou lançamento).

### Roles de Revisão

Use 3-5 especialistas conforme contexto:
- Growth strategist
- SEO/content strategist
- Conversion copy reviewer
- Paid media specialist
- Industry/domain expert

### Instrução por Revisor

Cada revisor deve:
1. Avaliar independentemente.
2. Identificar os 3 maiores riscos e oportunidades.
3. Propor correções concretas (não comentários genéricos).
4. Dar score de confiança de `0.0` a `1.0`.

### Synthesis

Em `review/expert-synthesis.md`, registrar:
- Zonas de concordância (high signal).
- Conflitos (onde especialistas divergem).
- Fixes prioritários por impacto esperado.
- Decisões tomadas com racional.

### Prompt Template para Revisores

```text
Revise este output de marketing a partir da sua lente especializada.

Role: [Growth / SEO / Conversion / Paid / Industry]
Goal: [objetivo de negócio]
Audience: [ICP]
Oferta principal: [oferta]
Ângulo escolhido: [ângulo]

Tarefas:
1) Liste os 3 maiores pontos fortes.
2) Liste os 3 maiores riscos ou fraquezas.
3) Proponha correções específicas.
4) Dê score de confiança (0-1).

Retorne feedback conciso e baseado em evidências.
```

### Regra de Decisão

Priorizar ações onde:
- 2+ revisores concordam, E
- confiança >= 0.7, E
- impacto esperado é alto.

Sugestões rejeitadas devem ser logadas com racional em `review/rejection-notes.md`.

---

<div align="center">

**👁️ Expert Review = Qualidade garantida**

</div>
