import { useState } from 'react';
import { ArrowLeft, Check, Copy, Download, RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import { useStore } from '../store';
import type { TemplateParameter } from '../types';
import { MarkdownPreview } from './MarkdownPreview';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Select } from './ui/Select';
import { Slider } from './ui/Slider';
import { Textarea } from './ui/Textarea';

export function Editor() {
  const {
    selectedTemplate,
    currentProject,
    controls,
    generatedContent,
    isGenerating,
    setView,
    setControl,
    setGeneratedContent,
    setIsGenerating,
    setPhase,
    createProject,
    updateProject,
  } = useStore();

  const [projectName, setProjectName] = useState(currentProject?.name || '');
  const [copied, setCopied] = useState(false);

  if (!selectedTemplate) {
    setView('templates');
    return null;
  }

  const handleGenerate = async () => {
    if (!projectName.trim()) {
      window.alert('Por favor, dê um nome ao projeto');
      return;
    }

    setIsGenerating(true);

    let project = currentProject;
    if (!project) {
      project = createProject(projectName);
    }

    try {
      const response = await api.generateContent({
        templateId: selectedTemplate.id,
        controls,
      });

      setGeneratedContent(response.content);
      setPhase('deliverable_ready');
      updateProject(project.id, {
        content: response.content,
        status: 'ready',
        name: projectName,
      });
    } catch (error) {
      console.error('Generation failed:', error);
      window.alert('Falha ao gerar conteúdo. Tente novamente.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(generatedContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([generatedContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${projectName || 'projeto'}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderControl = (param: TemplateParameter) => {
    const value = controls[param.id];

    switch (param.type) {
      case 'text':
        return (
          <Input
            key={param.id}
            label={param.label}
            placeholder={param.placeholder}
            value={String(value)}
            onChange={(e) => setControl(param.id, e.target.value)}
          />
        );

      case 'textarea':
        return (
          <Textarea
            key={param.id}
            label={param.label}
            placeholder={param.placeholder}
            value={String(value)}
            onChange={(e) => setControl(param.id, e.target.value)}
            rows={3}
          />
        );

      case 'slider':
        return (
          <Slider
            key={param.id}
            label={param.label}
            leftLabel="Formal"
            rightLabel="Casual"
            value={Number(value)}
            min={param.min}
            max={param.max}
            onChange={(v) => setControl(param.id, v)}
          />
        );

      case 'select':
        return (
          <Select
            key={param.id}
            label={param.label}
            value={String(value)}
            options={param.options || []}
            onChange={(v) => setControl(param.id, v)}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <header className="border-b border-gray-200 bg-white px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => setView('dashboard')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Voltar
            </Button>
            <div>
              <h1 className="font-semibold text-gray-900">{currentProject ? 'Editar Projeto' : 'Novo Projeto'}</h1>
              <p className="text-sm text-gray-500">{selectedTemplate.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {generatedContent && (
              <>
                <Button variant="secondary" size="sm" onClick={handleCopy}>
                  {copied ? <Check className="w-4 h-4 mr-2" /> : <Copy className="w-4 h-4 mr-2" />}
                  {copied ? 'Copiado!' : 'Copiar'}
                </Button>
                <Button variant="secondary" size="sm" onClick={handleDownload}>
                  <Download className="w-4 h-4 mr-2" />
                  Download
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-96 border-r border-gray-200 bg-gray-50 overflow-y-auto">
          <div className="p-6 space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Nome do Projeto</label>
              <Input
                placeholder="Ex: Campanha de Lançamento Q1"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
              />
            </div>

            <hr className="border-gray-200" />

            <div className="space-y-4">
              <h3 className="font-medium text-gray-900">Configurações</h3>
              {selectedTemplate.parameters.map(renderControl)}
            </div>

            <hr className="border-gray-200" />

            <Button onClick={handleGenerate} isLoading={isGenerating} disabled={!projectName.trim()} className="w-full">
              <RefreshCw className={`w-4 h-4 mr-2 ${isGenerating ? 'animate-spin' : ''}`} />
              {isGenerating ? 'Gerando...' : 'Gerar Conteúdo'}
            </Button>
          </div>
        </aside>

        <section className="flex-1 bg-white overflow-y-auto">
          <MarkdownPreview content={generatedContent} isLoading={isGenerating} />
        </section>
      </div>
    </div>
  );
}
