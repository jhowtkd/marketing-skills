import { FileText, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownPreviewProps {
  content: string;
  isLoading: boolean;
}

export function MarkdownPreview({ content, isLoading }: MarkdownPreviewProps) {
  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-12">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin mb-4" />
        <p className="text-gray-600 font-medium">Criando seu conteúdo...</p>
        <p className="text-sm text-gray-500 mt-1">Isso leva cerca de 30 segundos</p>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-12 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <FileText className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Pronto para criar</h3>
        <p className="text-gray-500 max-w-sm">
          Ajuste os controles à esquerda e clique em &quot;Gerar Conteúdo&quot; para criar seu material de marketing.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-8">
      <article className="editorial-prose prose prose-lg max-w-none text-slate-700">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </article>
    </div>
  );
}
