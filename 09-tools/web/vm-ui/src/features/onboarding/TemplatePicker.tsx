import React, { useState, useMemo, useCallback, useEffect } from 'react';
import type { Template, TemplateCategory } from './templates';
import { TEMPLATE_CATEGORIES, fillTemplatePrompt } from './templates';

// v38: One-click first run integration
interface FirstRunRecommendation {
  recommendedTemplate: string;
  oneClickReady: boolean;
  ctaText: string;
  contextualizedParams: Record<string, string>;
}

const fetchFirstRunRecommendation = async (
  userId: string,
  selectedTemplate?: string
): Promise<FirstRunRecommendation | null> => {
  try {
    const response = await fetch('/api/v2/onboarding/first-run/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        selected_template: selectedTemplate,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    return {
      recommendedTemplate: data.recommended_template,
      oneClickReady: data.one_click_ready,
      ctaText: data.cta_text,
      contextualizedParams: data.contextualized_params || {},
    };
  } catch (error) {
    console.warn('Failed to fetch first run recommendation:', error);
    return null;
  }
};

const executeOneClickFirstRun = async (
  userId: string,
  templateId: string,
  parameters: Record<string, string>
): Promise<{ success: boolean; output?: any; error?: string }> => {
  try {
    // First generate plan
    const planResponse = await fetch('/api/v2/onboarding/first-run/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        template_id: templateId,
        parameters,
      }),
    });
    
    if (!planResponse.ok) {
      throw new Error(`Plan HTTP ${planResponse.status}`);
    }
    
    const plan = await planResponse.json();
    
    if (!plan.one_click_ready) {
      return { success: false, error: 'Not ready for one-click execution' };
    }
    
    // Execute the plan
    const executeResponse = await fetch('/api/v2/onboarding/first-run/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        plan: {
          template_id: plan.template_id,
          status: plan.status,
          sanitized_params: plan.sanitized_params,
          estimated_duration_ms: plan.estimated_duration_ms,
        },
      }),
    });
    
    if (!executeResponse.ok) {
      throw new Error(`Execute HTTP ${executeResponse.status}`);
    }
    
    const result = await executeResponse.json();
    return {
      success: result.success,
      output: result.output,
      error: result.error,
    };
  } catch (error) {
    console.warn('One-click first run failed:', error);
    return { success: false, error: String(error) };
  }
};

interface TemplatePickerProps {
  templates: Template[];
  onSelect: (templateId: string, template: Template) => void;
  onCancel: () => void;
  selectedTemplateId?: string | null;
  recommendedTemplateId?: string | null;
  userId?: string; // v38: For one-click first run
  onFirstRunComplete?: (result: any) => void; // v38: Callback for one-click result
}

export const TemplatePicker: React.FC<TemplatePickerProps> = ({
  templates,
  onSelect,
  onCancel,
  selectedTemplateId,
  recommendedTemplateId,
  userId,
  onFirstRunComplete,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<TemplateCategory>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});
  
  // v38: One-click first run state
  const [firstRunRec, setFirstRunRec] = useState<FirstRunRecommendation | null>(null);
  const [isOneClickLoading, setIsOneClickLoading] = useState(false);
  const [oneClickResult, setOneClickResult] = useState<any>(null);

  const filteredTemplates = useMemo(() => {
    let result = templates;

    if (selectedCategory !== 'all') {
      result = result.filter((t) => t.category === selectedCategory);
    }

    if (searchQuery.trim()) {
      const normalizedQuery = searchQuery.toLowerCase().trim();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(normalizedQuery) ||
          t.description.toLowerCase().includes(normalizedQuery)
      );
    }

    return result;
  }, [templates, selectedCategory, searchQuery]);

  const selectedTemplate = useMemo(
    () => templates.find((t) => t.id === selectedTemplateId) || null,
    [templates, selectedTemplateId]
  );

  const handleTemplateClick = useCallback(
    (template: Template) => {
      onSelect(template.id, template);
      // Reset variable values when selecting new template
      setVariableValues({});
    },
    [onSelect]
  );

  const handleVariableChange = useCallback((name: string, value: string) => {
    setVariableValues((prev) => ({ ...prev, [name]: value }));
  }, []);

  const previewPrompt = useMemo(() => {
    if (!selectedTemplate) return '';
    return fillTemplatePrompt(selectedTemplate, variableValues);
  }, [selectedTemplate, variableValues]);

  const isRecommended = useCallback(
    (templateId: string) => templateId === recommendedTemplateId,
    [recommendedTemplateId]
  );

  // v38: Fetch first run recommendation
  useEffect(() => {
    if (!userId) return;
    
    const loadRecommendation = async () => {
      const rec = await fetchFirstRunRecommendation(userId, selectedTemplateId || undefined);
      if (rec) {
        setFirstRunRec(rec);
      }
    };
    
    loadRecommendation();
  }, [userId, selectedTemplateId]);
  
  // v38: Handle one-click first run
  const handleOneClickFirstRun = useCallback(async () => {
    if (!userId || !selectedTemplate) return;
    
    setIsOneClickLoading(true);
    
    const result = await executeOneClickFirstRun(
      userId,
      selectedTemplate.id,
      variableValues
    );
    
    setOneClickResult(result);
    setIsOneClickLoading(false);
    
    if (result.success && onFirstRunComplete) {
      onFirstRunComplete(result.output);
    }
  }, [userId, selectedTemplate, variableValues, onFirstRunComplete]);

  return (
    <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Escolha um Template
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Selecione um template para começar rápido e atingir seu primeiro valor
          </p>
        </div>
        {recommendedTemplateId && (
          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
            ⭐ Recomendado para primeiro valor
          </span>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="flex-1">
          <label htmlFor="search" className="sr-only">
            Buscar templates
          </label>
          <input
            id="search"
            type="text"
            placeholder="Buscar templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label htmlFor="category" className="sr-only">
            Categoria
          </label>
          <select
            id="category"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value as TemplateCategory)}
            className="w-full sm:w-48 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {TEMPLATE_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Template Grid */}
      {filteredTemplates.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {filteredTemplates.map((template) => (
            <button
              key={template.id}
              onClick={() => handleTemplateClick(template)}
              className={`relative text-left p-4 border rounded-lg transition-all hover:shadow-md ${
                selectedTemplateId === template.id
                  ? 'border-blue-500 ring-2 ring-blue-200 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              {/* Recommended Badge */}
              {isRecommended(template.id) && (
                <div className="absolute -top-2 -right-2">
                  <span className="inline-flex items-center rounded-full bg-green-500 px-2 py-0.5 text-xs font-medium text-white">
                    1º valor
                  </span>
                </div>
              )}

              <div className="flex items-start gap-3">
                <span className="text-2xl">{template.icon}</span>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-gray-900">{template.name}</h3>
                  <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                    {template.description}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 border border-dashed border-gray-300 rounded-lg mb-6">
          <p className="text-gray-500">Nenhum template encontrado</p>
          <p className="text-sm text-gray-400 mt-1">
            Tente ajustar seus filtros ou buscar por outro termo
          </p>
        </div>
      )}

      {/* Preview Panel */}
      {selectedTemplate && (
        <div className="border-t border-gray-200 pt-6 mb-6">
          <h3 className="font-medium text-gray-900 mb-4">
            Pré-visualização: {selectedTemplate.name}
          </h3>

          {/* Variable Inputs */}
          {selectedTemplate.variables && selectedTemplate.variables.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              {selectedTemplate.variables.map((variable) => (
                <div key={variable.name}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {variable.label}
                    {variable.required && <span className="text-red-500">*</span>}
                  </label>
                  <input
                    type="text"
                    placeholder={variable.placeholder}
                    value={variableValues[variable.name] || ''}
                    onChange={(e) =>
                      handleVariableChange(variable.name, e.target.value)
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Prompt Preview */}
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Prompt gerado
            </p>
            <p className="text-sm text-gray-700 font-mono whitespace-pre-wrap">
              {previewPrompt}
            </p>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
        >
          Cancelar
        </button>
        {selectedTemplate && (
          <>
            {/* v38: One-click first run button */}
            {firstRunRec?.oneClickReady && (
              <button
                onClick={handleOneClickFirstRun}
                disabled={isOneClickLoading}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-green-300 transition-colors flex items-center gap-2"
                data-testid="one-click-first-run"
              >
                {isOneClickLoading ? (
                  <>
                    <span className="animate-spin">⏳</span>
                    Gerando...
                  </>
                ) : (
                  <>
                    ⚡ {firstRunRec.ctaText}
                  </>
                )}
              </button>
            )}
            <button
              onClick={() => onSelect(selectedTemplate.id, selectedTemplate)}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Usar este template
            </button>
          </>
        )}
      </div>
      
      {/* v38: One-click result */}
      {oneClickResult && (
        <div 
          className={`mt-4 p-4 rounded-lg ${oneClickResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}
          data-testid="one-click-result"
        >
          {oneClickResult.success ? (
            <div>
              <p className="font-medium text-green-800">✅ Primeiro valor criado!</p>
              {oneClickResult.output && (
                <div className="mt-2 text-sm text-green-700">
                  <p><strong>{oneClickResult.output.title}</strong></p>
                  <p className="mt-1">{oneClickResult.output.preview}</p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-red-700">
              ❌ {oneClickResult.error || 'Falha ao criar conteúdo. Tente novamente.'}
            </p>
          )}
        </div>
      )}
    </div>
  );
};
