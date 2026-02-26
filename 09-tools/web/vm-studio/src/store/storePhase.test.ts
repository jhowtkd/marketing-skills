import { beforeEach, describe, expect, it } from 'vitest';
import type { SuggestedTemplate } from '../types';
import { useStore } from './index';

function resetStoreState(): void {
  useStore.setState({
    projects: [],
    selectedTemplate: null,
    currentProject: null,
    controls: {},
    generatedContent: '',
    isGenerating: false,
    currentView: 'dashboard',
    phase: 'chat_input',
    chatRequest: '',
    chatMessages: [],
    templateSuggestions: [],
    selectedSuggestedTemplateId: null,
    suggestionFallbackToManual: false,
  });
}

describe('chat-first phased store flow', () => {
  beforeEach(() => {
    resetStoreState();
  });

  it('moves from chat_input to template_suggestion when a chat request is submitted', () => {
    const initialState = useStore.getState();
    expect(initialState.phase).toBe('chat_input');

    initialState.startFromChatRequest('Preciso de uma landing page para SaaS B2B');

    const nextState = useStore.getState();
    expect(nextState.phase).toBe('template_suggestion');
    expect(nextState.chatRequest).toBe('Preciso de uma landing page para SaaS B2B');
    expect(nextState.chatMessages[nextState.chatMessages.length - 1]?.role).toBe('user');
  });

  it('tracks suggestions, selection, generation and refinement transitions', () => {
    const suggestions: SuggestedTemplate[] = [
      {
        templateId: 'landing-conversion',
        templateName: 'Landing Page de Conversão',
        summary: 'Copy para página de captura com CTA forte.',
        reason: 'Pedido menciona landing e conversão.',
      },
      {
        templateId: 'plan-launch-90d',
        templateName: 'Plano de Lançamento 90 dias',
        summary: 'Plano completo para lançamento com calendário.',
        reason: 'Ajuda a estruturar estratégia de campanha.',
      },
      {
        templateId: 'email-nurture',
        templateName: 'Sequência de Emails Nurture',
        summary: 'Fluxo de emails para aquecer leads.',
        reason: 'Complementa a etapa de conversão.',
      },
    ];

    const store = useStore.getState();
    store.startFromChatRequest('Quero ideias para campanha de lançamento');
    store.setTemplateSuggestions(suggestions);

    const withSuggestions = useStore.getState();
    expect(withSuggestions.templateSuggestions).toHaveLength(3);
    expect(withSuggestions.templateSuggestions[0]?.templateId).toBe('landing-conversion');
    expect(withSuggestions.suggestionFallbackToManual).toBe(false);

    withSuggestions.chooseSuggestedTemplate('email-nurture');

    const afterSelection = useStore.getState();
    expect(afterSelection.selectedSuggestedTemplateId).toBe('email-nurture');
    expect(afterSelection.selectedTemplate?.id).toBe('email-nurture');
    expect(afterSelection.phase).toBe('generating');

    afterSelection.setPhase('deliverable_ready');
    expect(useStore.getState().phase).toBe('deliverable_ready');

    afterSelection.appendChatMessage({
      id: 'msg-assistant-1',
      role: 'assistant',
      content: 'Aqui está seu primeiro draft.',
      createdAt: '2026-02-26T00:00:00.000Z',
    });
    const messages = useStore.getState().chatMessages;
    expect(messages[messages.length - 1]?.content).toContain('primeiro draft');

    afterSelection.setPhase('refining');
    expect(useStore.getState().phase).toBe('refining');
  });
});
