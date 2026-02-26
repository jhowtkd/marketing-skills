# VM Studio Deliverable-First Redesign Design

## Status
Proposta aprovada para implementacao.

---

## 1. Objetivo

Reposicionar o VM Studio como uma interface de entrega, nao como painel tecnico. O foco principal da tela deve ser a `Versao ativa` e o seu `entregavel principal`, com `aprovacoes e tarefas pendentes` como contexto operacional secundario.

Esse slice nao muda o backend nem cria fluxos fake. Ele reorganiza a experiencia em cima do runtime real ja existente.

---

## 2. Decisoes Validadas

- Modelo: `deliverable-first`
- Centro da experiencia: `preview da versao ativa`
- Painel secundario principal: `aprovacoes e tarefas pendentes`
- Intensidade visual: `redesign agressivo`
- Navegacao: `seletor no topo + contexto lateral reduzido`

---

## 3. Problema Atual

Mesmo com backend confiavel e UI funcional, a experiencia atual ainda comunica:

- painel tecnico
- excesso de caixas equivalentes
- falta de CTA dominante
- falta de hierarquia entre navegar, operar e consumir entrega
- preview ainda tratado como mais um bloco, nao como produto principal

Resultado: o usuario entende que "algo funciona", mas nao sente que esta operando uma agencia digital com entregaveis reais.

---

## 4. Solucao

## 4.1 Direcao de UX

O Studio vira um `canvas editorial`.

Estrutura:

- topo com seletores compactos de `Cliente`, `Campanha` e `Job`
- coluna esquerda fina para contexto e versoes
- coluna central dominante para o entregavel
- coluna direita para `Pendencias desta versao`

O principio e simples:

- navegar e leve
- ler o entregavel e central
- aprovar e agir e imediato
- debug fica escondido

## 4.2 Hierarquia da Tela

### Camada 1: Top Bar

Objetivo: trocar contexto sem parecer CRUD administrativo.

Conteudo:

- marca `VM Studio`
- seletores compactos:
  - `Cliente`
  - `Campanha`
  - `Job`
- acao primaria: `Gerar nova versao`
- toggle secundario: `Dev mode`

Comportamento:

- ao trocar contexto, a tela recarrega para a ultima `Versao ativa` do `Job`
- se nao houver versao, mostrar estado vazio editorial no centro

### Camada 2: Coluna Esquerda

Objetivo: reduzir a arvore e concentrar contexto util.

Blocos:

- `Modo`
  - `Chat`
  - `Studio`
- `Versoes`
  - lista curta com nome humano
  - status humano
  - destaque visual forte para a versao ativa
- `Contexto do Job`
  - resumo curto do que e aquele Job
  - sem IDs fora do `Dev mode`

Esta coluna deve parecer navegacao de produto, nao formulario de cadastro.

### Camada 3: Coluna Central

Objetivo: tornar o preview o produto principal.

Blocos:

- cabecalho da versao ativa
  - nome humano da versao
  - objetivo do pedido
  - status
  - hora/data
- barra de acoes
  - `Gerar nova versao`
  - `Baixar .md`
  - `Regenerar`
- preview Markdown rico
  - largura confortavel de leitura
  - tipografia editorial
  - destaque para headings, listas, quotes e tabelas
- estados vazios e de carregamento com linguagem humana

Regra:

- se existir `Versao ativa`, o preview ocupa a maior parte da interface
- se nao existir artefato, a coluna central nao mostra vazio tecnico; mostra orientacao clara do proximo passo

### Camada 4: Coluna Direita

Objetivo: deixar claro o que bloqueia ou continua a entrega.

Blocos:

- `Pendencias desta versao`
  - aprovacoes pendentes
  - tarefas pendentes
- CTA contextual
  - `Aprovar`
  - `Concluir`
  - `Comentar`
  - `Continuar fluxo`
- historico reduzido
  - secoes recolhidas para itens concluidos

Regra:

- o usuario deve entender em segundos o que precisa fazer para destravar a entrega

---

## 5. Linguagem de Produto

Termos visiveis:

- `Cliente`
- `Campanha`
- `Job`
- `Versao`
- `Entregavel`
- `Pendencias`

Termos escondidos por padrao:

- `thread_id`
- `run_id`
- `approval_id`
- `task_id`
- payload tecnico
- JSON bruto

`Dev mode` continua existindo, mas fica secundario e nao participa do fluxo principal.

---

## 6. Comportamentos Principais

## 6.1 Abrir um Job

- usuario escolhe `Cliente`, `Campanha` e `Job` no topo
- sistema carrega a ultima `Versao ativa` ou a mais recente
- centro mostra preview ou estado vazio orientado

## 6.2 Gerar nova versao

- CTA abre modal compacto
- campos:
  - `Objetivo do pedido`
  - `Perfil`
- ao confirmar:
  - versao entra na lista lateral
  - preview central entra em loading
  - coluna direita passa a refletir gates e tarefas

## 6.3 Aprovar ou concluir

- aprovacoes e tarefas sao executadas na direita
- apos acao, a versao ativa continua no centro
- a tela nao deve "sumir" ou tirar foco do entregavel

## 6.4 Regenerar

- acao secundaria associada ao entregavel ativo
- reaproveita contexto do Job e da versao atual
- deve ser lida como melhoria do resultado, nao como debug

## 6.5 Download

- botao `Baixar .md` sempre visivel quando houver artefato principal

---

## 7. Direcao Visual

## 7.1 Personalidade

Nao usar aparencia de dashboard generico.

Direcao:

- fundo com mais atmosfera e contraste sutil
- superfices claras, densas e bem definidas
- tipografia com cara editorial
- barras, cards e paineis com diferenca clara de peso visual
- preview com tratamento de documento

## 7.2 Paleta

Base sugerida:

- fundo: tons quentes e frios muito suaves, nao branco puro
- superficies: off-white e slate claro
- destaque primario: azul profundo ou petrolio
- estados:
  - pendente: ambar
  - concluido: verde
  - falha: vermelho queimado

## 7.3 Tipografia

Separar:

- tipografia de interface
- tipografia de documento

O preview precisa parecer um entregavel real, nao um bloco tecnico renderizado.

## 7.4 Motion

Motion discreta, com funcao:

- troca de versao
- loading do preview
- entrada de cards de pendencia
- feedback de CTA concluido

---

## 8. Arquitetura de Componentes

## 8.1 Estrutura proposta

- `AppShell`
  - `TopContextBar`
  - `SidebarRail`
  - `DeliverableCanvas`
  - `ActionRail`

## 8.2 Reuso de componentes existentes

Reaproveitar logica de hooks:

- `useWorkspace`
- `useInbox`

Refatorar apresentacao:

- [App.tsx](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/App.tsx)
- [NavigationPanel.tsx](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/features/navigation/NavigationPanel.tsx)
- [WorkspacePanel.tsx](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/features/workspace/WorkspacePanel.tsx)
- [InboxPanel.tsx](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/features/inbox/InboxPanel.tsx)
- [tailwind.css](/Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-ui/src/styles/tailwind.css)

Sem criar frontend paralelo.

---

## 9. Estados de Tela

## 9.1 Sem Job selecionado

- centro mostra mensagem forte e clara
- direita mostra nada operacional
- topo continua disponivel para selecao

## 9.2 Job sem versoes

- centro mostra convite para gerar a primeira versao
- CTA principal visivel

## 9.3 Versao carregando

- skeleton editorial no preview
- status claro no cabecalho

## 9.4 Versao aguardando aprovacao

- preview permanece visivel
- direita destaca pendencias
- CTA principal operacional fica no painel direito

## 9.5 Versao concluida

- preview completo
- download destacado
- historico de pendencias recolhido

## 9.6 Erro

- mensagem humana
- acao de recarregar
- `Dev mode` mostra detalhes tecnicos apenas se ligado

---

## 10. Testes

Cobrir:

- render do layout principal com `Versao ativa`
- estado vazio sem `Job`
- estado vazio sem artefato
- presenca de `Pendencias desta versao`
- persistencia de `Chat / Studio`
- `Baixar .md` no preview principal
- regressao de `Dev mode` escondendo IDs por padrao

---

## 11. Criterios de Sucesso

- o preview da versao ativa e claramente a parte mais importante da tela
- o usuario entende o que precisa aprovar sem procurar
- a interface deixa de parecer ferramenta interna
- o valor da entrega fica visivel em segundos
- a operacao continua apoiada no backend real, sem simulacao
