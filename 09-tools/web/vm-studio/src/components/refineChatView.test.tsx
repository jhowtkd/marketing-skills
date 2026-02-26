import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it } from 'vitest';
import App from '../App';
import { useStore } from '../store';
import type { Template, TemplateControls } from '../types';
import { RefineChatView } from './RefineChatView';

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function getDefaultControls(template: Template): TemplateControls {
  const controls: TemplateControls = {};
  for (const parameter of template.parameters) {
    controls[parameter.id] = parameter.defaultValue ?? (parameter.type === 'slider' ? 50 : '');
  }
  return controls;
}

function setupRoot(node: JSX.Element) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(node);
  });
  return { root, container };
}

function cleanupRoot(root: Root, container: HTMLDivElement): void {
  act(() => {
    root.unmount();
  });
  container.remove();
}

describe('RefineChatView', () => {
  beforeEach(() => {
    const template = useStore.getState().templates[0];
    expect(template).toBeDefined();

    act(() => {
      useStore.setState({
        selectedTemplate: template,
        controls: getDefaultControls(template),
        currentProject: {
          id: 'proj-refine-1',
          name: 'Campanha Editorial',
          templateId: template.id,
          templateName: template.name,
          status: 'ready',
          createdAt: '2026-02-26T00:00:00.000Z',
          updatedAt: '2026-02-26T00:00:00.000Z',
        },
        generatedContent: '# Entregável Base\n\n## Bloco principal\n\nTexto inicial.',
        chatMessages: [
          {
            id: 'msg-initial',
            role: 'user',
            content: 'Quero refinar este entregável.',
            createdAt: '2026-02-26T00:00:00.000Z',
          },
        ],
        phase: 'refining',
      });
    });
  });

  it('renders history and keeps deliverable context visible', () => {
    const { root, container } = setupRoot(<RefineChatView />);

    expect(container.textContent).toContain('Refinar no chat');
    expect(container.textContent).toContain('Histórico');
    expect(container.textContent).toContain('Entregável Base');
    expect(container.textContent).toContain('Quero refinar este entregável.');

    cleanupRoot(root, container);
  });

  it('sends a refine message and appends assistant response without backend', () => {
    const { root, container } = setupRoot(<RefineChatView />);

    const promptButton = Array.from(container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('foco em conversão')
    );
    expect(promptButton).toBeDefined();

    act(() => {
      promptButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const sendButton = Array.from(container.querySelectorAll('button')).find((button) => button.textContent?.includes('Enviar'));
    expect(sendButton).toBeDefined();

    act(() => {
      sendButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const messages = useStore.getState().chatMessages;
    expect(messages[messages.length - 2]?.role).toBe('user');
    expect(messages[messages.length - 1]?.role).toBe('assistant');
    expect(messages[messages.length - 1]?.content).toContain('Sem backend');

    cleanupRoot(root, container);
  });

  it('App renders refine chat view when phase is refining', () => {
    const { root, container } = setupRoot(<App />);

    expect(container.textContent).toContain('Refinar no chat');
    expect(container.textContent).toContain('Histórico');

    cleanupRoot(root, container);
  });
});
