import { ArrowLeft, MessageSquareText, Send } from 'lucide-react';
import { useMemo, useState } from 'react';
import { api } from '../api/client';
import { useStore } from '../store';
import { Button } from './ui/Button';
import { Textarea } from './ui/Textarea';

const QUICK_PROMPTS = [
  'Reescreva com foco em conversão e CTA mais direto.',
  'Deixe o texto mais objetivo para público B2B.',
  'Crie uma versão mais emocional mantendo a mesma estrutura.',
];

function extractDeliverableTitle(content: string): string {
  const firstLine = content
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line.length > 0);

  if (!firstLine) {
    return 'Entregável atual';
  }

  return firstLine.replace(/^#+\s*/, '');
}

export function RefineChatView() {
  const {
    currentProject,
    selectedTemplate,
    generatedContent,
    chatMessages,
    appendChatMessage,
    setGeneratedContent,
    updateProject,
    setPhase,
  } = useStore();
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const deliverableTitle = useMemo(() => extractDeliverableTitle(generatedContent), [generatedContent]);
  const deliverablePreview = useMemo(() => generatedContent.slice(0, 480), [generatedContent]);

  const sendMessage = async () => {
    const text = draft.trim();
    if (!text || isSending) {
      return;
    }

    appendChatMessage({
      id: `msg-user-${Date.now()}`,
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    });

    setDraft('');

    if (!currentProject) {
      appendChatMessage({
        id: `msg-assistant-${Date.now()}`,
        role: 'assistant',
        content: 'Nao encontrei projeto ativo para refinamento. Volte ao editor e tente novamente.',
        createdAt: new Date().toISOString(),
      });
      return;
    }

    const templateId = selectedTemplate?.id || currentProject.templateId;
    setIsSending(true);

    try {
      const response = await api.refineContent({
        templateId,
        prompt: text,
        currentContent: generatedContent,
        project: currentProject,
      });

      setGeneratedContent(response.content);
      updateProject(currentProject.id, {
        content: response.content,
        status: 'ready',
        backendContext: response.backendContext,
        lastRunId: response.runId,
      });

      appendChatMessage({
        id: `msg-assistant-${Date.now()}`,
        role: 'assistant',
        content: response.assistantSummary || `Refino aplicado para ${deliverableTitle}.`,
        createdAt: new Date().toISOString(),
      });
    } catch (error) {
      console.error('Refine failed:', error);
      appendChatMessage({
        id: `msg-assistant-${Date.now()}`,
        role: 'assistant',
        content: 'Nao consegui aplicar o refinamento agora. Tente novamente em instantes.',
        createdAt: new Date().toISOString(),
      });
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="editorial-surface min-h-screen px-6 py-8">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.3fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <header className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="editorial-kicker">Novo Projeto • Refino</p>
              <h1 className="mt-2 text-3xl font-semibold text-slate-900">Refinar no chat</h1>
              <p className="mt-2 text-sm text-slate-600">{currentProject?.name || 'Projeto ativo'}</p>
            </div>
            <Button variant="secondary" onClick={() => setPhase('deliverable_ready')}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Voltar ao entregável
            </Button>
          </header>

          <div className="mb-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-sm font-medium text-slate-800">Histórico</p>
            <div className="mt-3 max-h-[280px] space-y-3 overflow-y-auto pr-1">
              {chatMessages.length === 0 && <p className="text-sm text-slate-500">Nenhuma mensagem ainda.</p>}
              {chatMessages.map((message) => (
                <div
                  key={message.id}
                  className={`rounded-lg px-3 py-2 text-sm ${
                    message.role === 'user' ? 'ml-8 bg-primary-600 text-white' : 'mr-8 bg-white text-slate-700 border border-slate-200'
                  }`}
                >
                  {message.content}
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <Textarea
              label="Nova instrução"
              rows={4}
              placeholder="Ex: deixe o headline mais específico para gestores de marketing."
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setDraft(prompt)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 transition-colors hover:border-primary-300 hover:text-primary-700"
                >
                  {prompt}
                </button>
              ))}
            </div>
            <div className="flex justify-end">
              <Button onClick={sendMessage} disabled={!draft.trim() || isSending}>
                <Send className="mr-2 h-4 w-4" />
                {isSending ? 'Enviando...' : 'Enviar'}
              </Button>
            </div>
          </div>
        </section>

        <aside className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-3 flex items-center gap-2">
            <MessageSquareText className="h-4 w-4 text-primary-600" />
            <p className="text-sm font-semibold text-slate-900">Contexto do entregável</p>
          </div>
          <p className="text-sm text-slate-700">{deliverableTitle}</p>
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <pre className="whitespace-pre-wrap text-xs leading-relaxed text-slate-600">{deliverablePreview || 'Sem conteúdo gerado ainda.'}</pre>
          </div>
        </aside>
      </div>
    </div>
  );
}
