import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DeliverableView } from './DeliverableView';
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

function setupComponent() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => {
    root.render(<DeliverableView />);
  });
  return { root, container };
}

function cleanupComponent(root: Root, container: HTMLDivElement): void {
  act(() => {
    root.unmount();
  });
  container.remove();
}

describe('DeliverableView', () => {
  beforeEach(() => {
    const template = useStore.getState().templates[0];
    expect(template).toBeDefined();

    useStore.setState({
      selectedTemplate: template,
      controls: getDefaultControls(template),
      currentProject: {
        id: 'proj-test-1',
        name: 'Lançamento Editorial',
        templateId: template.id,
        templateName: template.name,
        status: 'ready',
        createdAt: '2026-02-26T00:00:00.000Z',
        updatedAt: '2026-02-26T00:00:00.000Z',
      },
      generatedContent: '# Headline principal\n\n## Oferta\n\nTexto inicial do entregável.',
      isGenerating: false,
      phase: 'deliverable_ready',
    });
  });

  it('renders deliverable-first structure with content and next steps', () => {
    const { root, container } = setupComponent();

    expect(container.textContent).toContain('Entregável pronto');
    expect(container.textContent).toContain('Próximos passos');
    expect(container.textContent).toContain('Headline principal');
    expect(container.textContent).toContain('Oferta');

    cleanupComponent(root, container);
  });

  it('uses "Refinar no chat" as explicit primary CTA and moves to refining phase', () => {
    const appendSpy = vi.spyOn(useStore.getState(), 'appendChatMessage');
    const { root, container } = setupComponent();

    const refineButton = Array.from(container.querySelectorAll('button')).find((button) =>
      button.textContent?.includes('Refinar no chat')
    );
    expect(refineButton).toBeDefined();

    act(() => {
      refineButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect(useStore.getState().phase).toBe('refining');
    expect(appendSpy).toHaveBeenCalledTimes(1);

    appendSpy.mockRestore();
    cleanupComponent(root, container);
  });
});
