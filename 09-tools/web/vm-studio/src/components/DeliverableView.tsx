import { Bot, MessageSquare, PenSquare, RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useStore } from '../store';
import { Button } from './ui/Button';

const NEXT_STEPS = [
  'Ajuste tom e promessa principal para o canal de distribuição.',
  'Revise os CTAs para manter um único objetivo de conversão por peça.',
  'Use “Refinar no chat” para gerar variações orientadas por feedback.',
];

export function DeliverableView() {
  const { currentProject, generatedContent, phase, setPhase, appendChatMessage } = useStore();

  const handleRefine = () => {
    setPhase('refining');
    appendChatMessage({
      id: `msg-${Date.now()}`,
      role: 'user',
      content: 'Quero refinar este entregável.',
      createdAt: new Date().toISOString(),
    });
  };

  const handleBackToEditor = () => {
    setPhase('generating');
  };

  return (
    <div className="editorial-surface min-h-screen px-6 py-8">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-2xl border border-slate-200 bg-white/95 p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="editorial-kicker">Novo Projeto</p>
              <h1 className="mt-2 text-3xl font-semibold text-slate-900">Entregável pronto</h1>
              <p className="mt-2 text-sm text-slate-600">
                {currentProject?.name || 'Projeto sem nome'} • {phase === 'refining' ? 'Refinando no chat' : 'Pronto para revisão'}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={handleRefine}>
                <MessageSquare className="mr-2 h-4 w-4" />
                Refinar no chat
              </Button>
              <Button variant="secondary" onClick={handleBackToEditor}>
                <PenSquare className="mr-2 h-4 w-4" />
                Voltar ao editor
              </Button>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Entregável principal</h2>
            <div className="mt-4 border-t border-slate-100 pt-4">
              {generatedContent ? (
                <article className="editorial-prose prose max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{generatedContent}</ReactMarkdown>
                </article>
              ) : (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-slate-600">
                  <RefreshCw className="mx-auto mb-3 h-5 w-5 animate-spin text-primary-600" />
                  O conteúdo ainda está sendo preparado.
                </div>
              )}
            </div>
          </section>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="text-base font-semibold text-slate-900">Próximos passos</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-700">
                {NEXT_STEPS.map((step) => (
                  <li key={step} className="flex items-start gap-2">
                    <Bot className="mt-0.5 h-4 w-4 shrink-0 text-primary-600" />
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-sm font-medium text-slate-800">CTA primário</p>
              <p className="mt-1 text-sm text-slate-600">
                Use <strong>Refinar no chat</strong> para iterar com instruções rápidas sem perder contexto.
              </p>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
