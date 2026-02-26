import { AlertTriangle, ArrowLeft, CheckCircle2, Wand2 } from 'lucide-react';
import { useStore } from '../store';
import { Button } from './ui/Button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './ui/Card';

export function TemplateSuggestionView() {
  const {
    chatRequest,
    templateSuggestions,
    suggestionFallbackToManual,
    chooseSuggestedTemplate,
    setPhase,
    setView,
  } = useStore();

  const handleManualSelection = () => {
    setView('templates');
    setPhase('generating');
  };

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Templates sugeridos</h1>
            <p className="mt-1 text-sm text-gray-600">
              Pedido: <span className="font-medium text-gray-800">{chatRequest || 'Sem contexto informado'}</span>
            </p>
          </div>
          <Button variant="ghost" onClick={() => setPhase('chat_input')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Voltar ao pedido
          </Button>
        </div>

        {suggestionFallbackToManual && (
          <div className="mb-6 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <div className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                Sinal fraco no pedido: mostramos um fallback determinístico e também a seleção manual para manter o fluxo.
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {templateSuggestions.map((suggestion) => (
            <Card key={suggestion.templateId} className="flex h-full flex-col">
              <CardHeader>
                <CardTitle>{suggestion.templateName}</CardTitle>
                <CardDescription>{suggestion.summary}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <div className="rounded-lg border border-primary-100 bg-primary-50 px-3 py-2 text-sm text-primary-800">
                  <div className="mb-1 flex items-center gap-2 font-medium">
                    <Wand2 className="h-4 w-4" />
                    Por que esse template
                  </div>
                  <p>{suggestion.reason}</p>
                </div>
              </CardContent>
              <CardFooter>
                <Button className="w-full" onClick={() => chooseSuggestedTemplate(suggestion.templateId)}>
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Selecionar template
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>

        <div className="mt-6">
          <Button variant="secondary" onClick={handleManualSelection}>
            Escolher manualmente
          </Button>
        </div>
      </div>
    </div>
  );
}
