import React, { useState, useMemo, useCallback } from 'react';
import type { Template, TemplateCategory } from './templates';
import { TEMPLATE_CATEGORIES, fillTemplatePrompt } from './templates';

interface TemplatePickerProps {
  templates: Template[];
  onSelect: (templateId: string, template: Template) => void;
  onCancel: () => void;
  selectedTemplateId?: string | null;
  recommendedTemplateId?: string | null;
}

export const TemplatePicker: React.FC<TemplatePickerProps> = ({
  templates,
  onSelect,
  onCancel,
  selectedTemplateId,
  recommendedTemplateId,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<TemplateCategory>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [variableValues, setVariableValues] = useState<Record<string, string>>({});

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
          <button
            onClick={() => onSelect(selectedTemplate.id, selectedTemplate)}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Usar este template
          </button>
        )}
      </div>
    </div>
  );
};
