# 🔍 Research Framework

> Sistema completo de pesquisa de mercado usando ferramentas gratuitas.

---

## 🎯 Objetivo

Coletar inteligência de mercado estruturada para embasar decisões de marketing.

---

## 🛠️ Ferramentas Utilizadas

| Ferramenta | Uso | Custo |
|------------|-----|-------|
| DuckDuckGo | Busca web | Grátis |
| BeautifulSoup | Scraping HTML | Grátis |
| Playwright | Automação de browser | Grátis |

---

## 📋 Framework de Pesquisa: 6 Circles Method

```
        ┌─────────────────┐
        │   1. MARKET     │  ← Tamanho, tendências, crescimento
        │    (Mercado)    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │   2. COMPETITION│  ← Concorrentes diretos e indiretos
        │  (Concorrência) │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │   3. CUSTOMER   │  ← Público-alvo, personas, dores
        │    (Cliente)    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │   4. COMPANY    │  ← Sua posição, recursos, vantagens
        │    (Empresa)    │
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │   5. COLLABORATORS│ ← Parceiros, fornecedores, canais
        │  (Colaboradores)│
        └────────┬────────┘
                 │
        ┌────────▼────────┐
        │   6. CLIMATE    │  ← Ambiente: político, econômico, social
        │    (Clima)      │
        └─────────────────┘
```

---

## 🔬 Processo de Pesquisa

### Fase 1: Market Analysis

**Objetivo:** Entender o mercado como um todo

**Perguntas-chave:**
- Qual o tamanho do mercado (TAM, SAM, SOM)?
- Qual a taxa de crescimento?
- Quais as tendências atuais?
- Existem barreiras de entrada?

**Fontes de dados:**
- Relatórios de mercado gratuitos
- Google Trends
- Notícias do setor
- Redes sociais

**Template de Output:**
```markdown
## Market Analysis

### Tamanho do Mercado
- TAM (Total Addressable Market): 
- SAM (Serviceable Addressable Market): 
- SOM (Serviceable Obtainable Market): 

### Crescimento
- Taxa anual: 
- Projeção 5 anos: 

### Tendências
1. [Tendência 1]
2. [Tendência 2]
3. [Tendência 3]

### Oportunidades
- [Oportunidade 1]
- [Oportunidade 2]
```

---

### Fase 2: Competition Analysis

**Objetivo:** Mapear e analisar concorrentes

**Template de Análise Competitiva:**
```markdown
## Competition Analysis

### Concorrente 1: [Nome]
**Website:** [URL]
**Posicionamento:** [Uma frase]

#### Produtos/Serviços
- [Produto 1]: R$ [preço]
- [Produto 2]: R$ [preço]

#### Proposta de Valor
[Descreva a proposta principal]

#### Pontos Fortes
- [Ponto 1]
- [Ponto 2]

#### Pontos Fracos
- [Ponto 1]
- [Ponto 2]

#### Estratégia de Marketing
- Canais: [lista]
- Tom de voz: [descrição]
- Diferencial: [descrição]

### Análise Comparativa
| Aspecto | Nós | Concorrente 1 | Concorrente 2 |
|---------|-----|---------------|---------------|
| Preço | | | |
| Qualidade | | | |
| Velocidade | | | |
| Suporte | | | |
```

---

### Fase 3: Customer Research

**Objetivo:** Entender profundamente o público-alvo

**Framework: Starving Crowd (Gary Halbert)**

```
A pergunta mais importante do marketing:

"Eu escolheria ter um produto MEDIOCRE
com acesso a uma MULTIDÃO FAMINTA,
ou um produto EXCELENTE sem acesso
a essa multidão?"

Resposta: SEMPRE escolha a multidão faminta.
```

**Template de Customer Research:**
```markdown
## Customer Research

### Demográficos
- Idade: 
- Gênero: 
- Renda: 
- Localização: 
- Educação: 
- Ocupação: 

### Psicográficos
- Valores: 
- Interesses: 
- Estilo de vida: 
- Dores principais: 
- Desejos: 
- Medos: 

### Comportamento
- Onde buscam informação? 
- Onde compram? 
- Quem influencia? 
- Ciclo de compra: 

### Jobs-to-be-Done
1. [Job 1]: [contexto]
2. [Job 2]: [contexto]
3. [Job 3]: [contexto]

### Objections (Objeções)
- [Objeção 1]
- [Objeção 2]
- [Objeção 3]

### Language (Linguagem)
- Termos que usam: 
- Frases comuns: 
- Tom preferido: 
```

---

### Fase 4: Company Analysis

**Objetivo:** Analisar sua própria posição

**Template:**
```markdown
## Company Analysis

### Recursos
- Financeiros: 
- Humanos: 
- Tecnológicos: 
- Relacionamentos: 

### Capacidades
- O que fazemos bem? 
- O que nos diferencia? 
- Qual nossa vantagem competitiva? 

### Limitações
- O que precisamos melhorar? 
- Onde somos fracos? 
- O que nos falta? 

### Oportunidades Internas
- [Oportunidade 1]
- [Oportunidade 2]

### Ameaças Internas
- [Ameaça 1]
- [Ameaça 2]
```

---

### Fase 5: Collaborators Analysis

**Objetivo:** Mapear parceiros e canais

**Template:**
```markdown
## Collaborators Analysis

### Parceiros Potenciais
- [Parceiro 1]: [benefício]
- [Parceiro 2]: [benefício]

### Canais de Distribuição
- Direto: 
- Indireto: 
- Online: 
- Offline: 

### Fornecedores
- [Fornecedor 1]: [importância]
- [Fornecedor 2]: [importância]

### Influenciadores
- [Influenciador 1]: [alcance/relevância]
- [Influenciador 2]: [alcance/relevância]
```

---

### Fase 6: Climate Analysis

**Objetivo:** Analisar o ambiente externo

**Template (PESTEL):**
```markdown
## Climate Analysis (PESTEL)

### Political (Político)
- Regulamentações: 
- Políticas governamentais: 
- Estabilidade política: 

### Economic (Econômico)
- Crescimento econômico: 
- Inflação: 
- Taxa de câmbio: 
- Poder aquisitivo: 

### Social (Social)
- Demografia: 
- Cultura: 
- Estilo de vida: 
- Valores: 

### Technological (Tecnológico)
- Inovações: 
- Automação: 
- Mudanças tecnológicas: 

### Environmental (Ambiental)
- Sustentabilidade: 
- Regulamentações ambientais: 
- Consciência ecológica: 

### Legal (Legal)
- Leis de proteção ao consumidor: 
- Leis de privacidade: 
- Propriedade intelectual: 
```

---

## 🎯 Output Consolidado

```markdown
# Research Report: [Nome do Projeto]
Data: [Data]
Pesquisador: [Nome]

## Executive Summary
[Resumo executivo em 3-5 parágrafos]

## Key Findings
1. [Descoberta principal 1]
2. [Descoberta principal 2]
3. [Descoberta principal 3]

## Strategic Implications
- [Implicação 1]
- [Implicação 2]
- [Implicação 3]

## Recommendations
1. [Recomendação 1]
2. [Recomendação 2]
3. [Recomendação 3]

## Next Steps
- [Próximo passo 1]
- [Próximo passo 2]
```

---

## 🛠️ Implementação com Python

```python
# research_tools.py - Exemplo de uso
from research_tools import MarketResearch

# Inicializar
research = MarketResearch()

# Pesquisar mercado
market_data = research.search_market("cursos de Python Brasil")

# Analisar concorrentes
competitors = research.analyze_competitors([
    "competidor1.com.br",
    "competidor2.com.br"
])

# Gerar relatório
report = research.generate_report(market_data, competitors)
```

---

## 📊 Checklist de Pesquisa

- [ ] Market size identificado
- [ ] Concorrentes mapeados (mínimo 3)
- [ ] Público-alvo definido
- [ ] Dores do cliente identificadas
- [ ] Propostas de valor analisadas
- [ ] Preços de mercado coletados
- [ ] Gaps identificados
- [ ] Oportunidades listadas
- [ ] Relatório consolidado
- [ ] Recomendações claras

---

<div align="center">

**🔍 Pesquisa completa = Decisões inteligentes**

</div>
