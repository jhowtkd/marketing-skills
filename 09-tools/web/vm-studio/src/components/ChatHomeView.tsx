import { MessageSquareText, Sparkles } from 'lucide-react';
import { useState } from 'react';
import { suggestTemplatesFromRequest } from '../api/client';
import { useStore } from '../store';
import { Button } from './ui/Button';
import { Textarea } from './ui/Textarea';

const EXAMPLE_REQUESTS = [
  'Quero uma landing page para converter leads de consultoria B2B.',
  'Preciso de uma sequência de emails para nutrir trial de SaaS.',
  'Monte um plano de lançamento de 90 dias para um curso online.',
];

export function ChatHomeView() {
  const { chatRequest, templates, startFromChatRequest, setTemplateSuggestions } = useStore();
  const [requestText, setRequestText] = useState(chatRequest);

  const submitRequest = () => {
    const trimmedRequest = requestText.trim();
    if (!trimmedRequest) {
      return;
    }

    startFromChatRequest(trimmedRequest);
    const suggestionResult = suggestTemplatesFromRequest(trimmedRequest, templates);
    setTemplateSuggestions(suggestionResult.suggestions, suggestionResult.fallbackToManualSelection);
  };

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 flex items-center gap-3">
          <div className="rounded-xl bg-primary-100 p-3 text-primary-700">
            <MessageSquareText className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">O que você quer criar hoje?</h1>
            <p className="mt-1 text-sm text-gray-600">Descreva seu objetivo e eu sugiro 3 templates para começar.</p>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <Textarea
            label="Pedido inicial"
            placeholder="Ex: Quero uma campanha de lançamento para um produto B2B."
            rows={5}
            value={requestText}
            onChange={(event) => setRequestText(event.target.value)}
          />

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-gray-500">Use linguagem natural. Quanto mais contexto, melhor a sugestão.</p>
            <Button onClick={submitRequest} disabled={!requestText.trim()}>
              <Sparkles className="mr-2 h-4 w-4" />
              Gerar sugestões
            </Button>
          </div>
        </div>

        <div className="mt-6">
          <p className="mb-3 text-sm font-medium text-gray-700">Exemplos rápidos</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_REQUESTS.map((example) => (
              <button
                key={example}
                onClick={() => setRequestText(example)}
                className="rounded-full border border-gray-200 bg-white px-4 py-2 text-sm text-gray-700 transition-colors hover:border-primary-300 hover:text-primary-700"
                type="button"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
