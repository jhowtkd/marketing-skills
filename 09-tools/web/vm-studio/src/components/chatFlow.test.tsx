import { beforeEach, describe, expect, it } from 'vitest';
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import App from '../App';
import { useStore } from '../store';
import type { Template, TemplateControls } from '../types';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function getDefaultControls(template: Template): TemplateControls {
  const controls: TemplateControls = {};
  for (const parameter of template.parameters) {
    controls[parameter.id] = parameter.defaultValue ?? (parameter.type === 'slider' ? 50 : '');
  }
  return controls;
}

function resetStoreState(): void {
  const templates = useStore.getState().templates;

  useStore.setState({
    projects: [],
    templates,
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

function setupApp() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(<App />);
  });
  return { container, root };
}

function cleanupApp(root: Root, container: HTMLDivElement): void {
  act(() => {
    root.unmount();
  });
  container.remove();
}

describe('chat-first app flow', () => {
  beforeEach(() => {
    act(() => {
      resetStoreState();
    });
  });

  it('renders chat-first home in chat_input phase', () => {
    const { container, root } = setupApp();

    expect(container.textContent).toContain('O que você quer criar hoje?');
    expect(container.textContent).toContain('Gerar sugestões');

    cleanupApp(root, container);
  });

  it('transitions from chat input to template suggestion and then to generating', () => {
    const { container, root } = setupApp();

    const exampleButton = Array.from(container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('landing page')
    );
    expect(exampleButton).toBeDefined();

    act(() => {
      exampleButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const submitButton = Array.from(container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Gerar sugestões')
    );

    expect(submitButton).toBeDefined();

    act(() => {
      submitButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(useStore.getState().phase).toBe('template_suggestion');
    expect(container.textContent).toContain('Templates sugeridos');

    const selectButtons = Array.from(container.querySelectorAll('button')).filter((button) =>
      button.textContent?.includes('Selecionar template')
    );
    expect(selectButtons).toHaveLength(3);

    act(() => {
      selectButtons[0]!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(useStore.getState().phase).toBe('generating');
    expect(container.textContent).toContain('Novo Projeto');

    cleanupApp(root, container);
  });

  it('renders editor when phase is deliverable_ready or refining', () => {
    const template = useStore.getState().templates[0];
    expect(template).toBeDefined();

    useStore.setState({
      selectedTemplate: template,
      controls: getDefaultControls(template),
      phase: 'deliverable_ready',
    });

    const { container, root } = setupApp();

    expect(container.textContent).toContain('Novo Projeto');

    act(() => {
      useStore.getState().setPhase('refining');
    });

    expect(container.textContent).toContain('Novo Projeto');

    cleanupApp(root, container);
  });
});
