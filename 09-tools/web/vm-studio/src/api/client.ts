const API_BASE = '/api/v2';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export interface GenerateRequest {
  templateId: string;
  controls: Record<string, string | number>;
}

export interface GenerateResponse {
  content: string;
  runId?: string;
}

export const api = {
  async generateContent(request: GenerateRequest): Promise<GenerateResponse> {
    await new Promise((resolve) => setTimeout(resolve, 2000));

    return {
      content: generatePlaceholderContent(request),
    };
  },

  async getWorkflowStatus(runId: string): Promise<{ status: string; content?: string }> {
    return fetchJson(`${API_BASE}/workflow-runs/${runId}`);
  },
};

function generatePlaceholderContent(request: GenerateRequest): string {
  const { templateId, controls } = request;
  const productName = controls.productName || 'Seu Produto';

  if (templateId === 'landing-conversion') {
    return `# Landing Page: ${productName}

## Hero

**Headline:** Transforme ${controls.problem || 'seu desafio'} em resultados reais

**Subheadline:** ${productName} é a solução que ${controls.solution || 'resolve seu problema'} sem complicação.

**CTA:** [Quero saber mais]

---

## O Problema

Você está perdendo tempo e dinheiro com ${controls.problem || 'processos manuais'}.

- ❌ Horas desperdiçadas em tarefas repetitivas
- ❌ Resultados abaixo do esperado
- ❌ Frustração com soluções complicadas

---

## A Solução

${productName} veio para mudar isso:

✅ **Simples:** Configuração em minutos, não dias  
✅ **Eficiente:** ${controls.solution || 'Resultados imediatos'}  
✅ **Confiável:** Usado por centenas de empresas

---

## Prova Social

> "Dobramos nossa produtividade em 30 dias usando ${productName}."
> — Cliente Satisfeito

---

## CTA Final

Não deixe ${controls.problem || 'seu problema'} te segurar.

**[Começar agora]**
`;
  }

  if (templateId === 'email-nurture') {
    return `# Sequência de Emails: ${productName}

## Email 1: Boas-vindas

**Assunto:** Bem-vindo! Aqui está o que você precisa saber

Olá!

Obrigado por se juntar a nós. Você fez a escolha certa ao buscar ${controls.solution || 'uma solução melhor'}.

Nos próximos dias, vou te mostrar exatamente como ${productName} pode transformar seus resultados.

Fique atento ao próximo email!

Abraços,
Equipe ${productName}

---

## Email 2: O Problema

**Assunto:** Você está cometendo esse erro?

Oi,

Você sabia que 80% das empresas perdem dinheiro por causa de ${controls.problem || 'ineficiência'}?

A boa notícia: existe uma solução simples.

${productName} foi criado especificamente para resolver isso.

Quer ver como? Responde esse email.

---

## Email 3: A Solução

**Assunto:** Como [Cliente] dobrou os resultados em 30 dias

Olá,

Hoje quero te contar a história da [Empresa Cliente].

Eles enfrentavam exatamente o mesmo problema que você: ${controls.problem || 'desafios crescentes'}.

Em 30 dias usando ${productName}, eles conseguiram:

- ✅ Resultado 1
- ✅ Resultado 2  
- ✅ Resultado 3

Quer resultados similares?

**[Agendar demonstração]**
`;
  }

  return `# Plano de Lançamento: ${productName}

## Resumo Executivo

Lançamento estratégico de ${productName} para ${controls.audience || 'seu público-alvo'}.

**Foco:** ${controls.focus || 'conversão'}  
**Duração:** 90 dias

---

## Fase 1: Pré-lançamento (Dias 1-30)

### Semana 1-2: Pesquisa e Posicionamento
- [ ] Mapear 5 principais concorrentes
- [ ] Definir proposta de valor única
- [ ] Criar landing page de espera

### Semana 3-4: Construção de Audiência
- [ ] Publicar 4 posts educativos
- [ ] Criar lead magnet relacionado
- [ ] Iniciar anúncios de awareness

---

## Fase 2: Lançamento (Dias 31-60)

### Semana 5-6: Abertura
- [ ] Email de lançamento para lista
- [ ] Lives de demonstração
- [ ] Cases de early adopters

### Semana 7-8: Aceleração
- [ ] Urgência e escassez
- [ ] Depoimentos em vídeo
- [ ] Bônus por tempo limitado

---

## Fase 3: Pós-lançamento (Dias 61-90)

- [ ] Onboarding dos novos clientes
- [ ] Campanha de indicação
- [ ] Conteúdo de sucesso de clientes
`;
}
