# 🚀 Vibe Marketing - Quickstart (5 Minutos)

> Do zero à sua primeira campanha em 5 minutos.

---

## ⚡ Instalação Rápida

### 1. Clone a Skill (30 segundos)

```bash
git clone <repo-url> vibe-marketing-skill
cd vibe-marketing-skill
```

### 2. Instale Dependências (2 minutos)

```bash
# Linux/Mac
bash 09-tools/setup.sh

# Windows
python -m pip install -r 09-tools/requirements.txt
```

### GUI Local (Opcional)

Para interface gráfica de onboarding:

```bash
python3 09-tools/onboard_web.py serve
# Acesse http://127.0.0.1:8765
```

### 3. Configure sua IDE (1 minuto)

**Codex:**
```yaml
# Cole em .codex/config.yaml
skills:
  - path: ./vibe-marketing-skill
    command: "@vibe"
```

**Kimi Code:**
```yaml
# Cole em .kimi/skills.yaml
skills:
  vibe-marketing:
    path: ./vibe-marketing-skill
    trigger: "/vibe"
```

**Antigravity:**
```yaml
# Cole em .antigravity/skills.yaml
skills:
  - name: vibe-marketing
    path: ./vibe-marketing-skill
    prefix: "vibe:"
```

---

## 🎯 Primeiro Uso (2 minutos)

### Opção 1: Workflow Completo

```
@vibe
Quero criar uma landing page para um curso de Python
para iniciantes. Meu público são profissionais de 
administração que querem automatizar planilhas.
```

O orchestrator vai:
1. Fazer pesquisa de mercado
2. Definir posicionamento
3. Criar copy completa
4. Gerar brief criativo

### Opção 2: Componente Específico

```
@vibe-research
Analise o mercado de cursos de Python no Brasil.
Foque em: preços, propostas de valor, gaps.
```

```
@vibe-copy
Crie uma headline para landing page de curso Python
usando PAS (Problem-Agitate-Solution).
Produto: Curso Python para Automatizar Planilhas
Público: Administradores, 25-40 anos
```

---

## 📋 Workflows Disponíveis

| Comando | Descrição | Tempo |
|---------|-----------|-------|
| `@vm-research` | Pesquisa de mercado completa | 10-15 min |
| `@vm-foundation` | Fundação de marca | 15-20 min |
| `@vm-landing` | Landing page completa | 20-30 min |
| `@vm-email-seq` | Sequência de 7 emails | 15-20 min |
| `@vm-seo-content` | Artigo SEO otimizado | 20-30 min |
| `@vm-atomize` | 1 conteúdo → 15+ peças | 10-15 min |

---

## 🔧 Stacks Prontas

### Foundation Stack
```
@vibe-stack-foundation
Projeto: [nome do projeto]
Descrição: [breve descrição]
```
**Output:** Brand Voice + Positioning + Keywords

### Conversion Stack
```
@vibe-stack-conversion
Produto: [nome do produto]
Preço: [valor]
Público: [descrição]
```
**Output:** Landing + Email Sequence + Lead Magnet

### Traffic Stack
```
@vibe-stack-traffic
Tópico: [tema principal]
Palavras-chave: [3-5 termos]
```
**Output:** SEO Content + Social Posts + Ad Creative

### Nurture Stack
```
@vibe-stack-nurture
Lead Magnet: [descrição]
Objetivo: [qualificação/venda]
```
**Output:** Welcome Sequence + Newsletter + Content

---

## 💡 Exemplos Práticos

### Exemplo 1: Curso Online

```
@vibe-landing
Produto: Curso de Fotografia para Iniciantes
Preço: R$ 497
Público: Pessoas 25-45 anos que compraram câmera
                    mas não saem do automático
Diferencial: Método 5-passos, sem termos técnicos
```

### Exemplo 2: Serviço B2B

```
@vibe-research
Mercado: Software de gestão para clínicas médicas
Região: São Paulo e Rio de Janeiro
Concorrentes: [lista 3-5]
```

### Exemplo 3: Produto Físico

```
@vibe-email-seq
Produto: Suplemento natural para sono
Preço: R$ 127/mês
Público: Profissionais estressados, 30-50 anos
Lead Magnet: E-book "7 Rituais para Dormir Bem"
```

---

## 🎮 Comandos de Revisão

Após criar qualquer asset, use:

```
@vibe-review-copy
[COLE SUA COPY AQUI]
Framework usado: [AIDA/PAS/etc]
Objetivo: [clique/cadastro/compra]
```

```
@vibe-review-strategy
[COLE SUA ESTRATÉGIA AQUI]
Contexto: [breve descrição]
```

---

## 📁 Onde Encontrar as Saídas

Tudo é salvo em `08-output/`:

```
08-output/
├── YYYY-MM-DD/
│   ├── research/
│   ├── strategy/
│   ├── copy/
│   ├── creative/
│   └── final/
```

---

## 🆘 Troubleshooting

### "Não reconhece o comando"
- Verifique se a skill está no path correto
- Reinicie a IDE
- Confira a configuração em `.skill/manifest.json`

### "Erro nas ferramentas Python"
```bash
# Reinstale dependências
pip install --upgrade -r 09-tools/requirements.txt
```

### "Contexto muito longo"
- Use `@vm-checkpoint-save` para salvar progresso
- Continue com `@vm-continue`
- Ou divida em partes menores

---

## 📚 Próximos Passos

1. **Explore os templates** em `08-templates/`
2. **Leia os frameworks** em `02-methodology/`
3. **Experimente stacks** em `06-stacks/`
4. **Personalize** `vibe.config.yaml`

---

## 🎯 Checklist de Primeiro Projeto

- [ ] Instalou dependências
- [ ] Configurou IDE
- [ ] Rodou primeiro comando
- [ ] Revisou output
- [ ] Salvou assets
- [ ] Iterou com feedback

---

<div align="center">

**Pronto! Você já sabe usar Vibe Marketing.** 🎉

[📖 Documentação Completa](README.md) | [⚙️ Arquitetura](ARCHITECTURE.md)

</div>
