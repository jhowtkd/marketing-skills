export interface Project {
  id: string;
  name: string;
  templateId: string;
  templateName: string;
  status: 'ready' | 'generating' | 'draft';
  content?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  tags: string[];
  estimatedTime: string;
  parameters: TemplateParameter[];
}

export interface TemplateParameter {
  id: string;
  type: 'text' | 'select' | 'slider' | 'textarea';
  label: string;
  placeholder?: string;
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
  defaultValue?: string | number;
}

export interface TemplateControls {
  [key: string]: string | number;
}

export type StudioPhase = 'chat_input' | 'template_suggestion' | 'generating' | 'deliverable_ready' | 'refining';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
}

export interface SuggestedTemplate {
  templateId: string;
  templateName: string;
  summary: string;
  reason: string;
}

export interface AppState {
  projects: Project[];
  templates: Template[];
  selectedTemplate: Template | null;
  currentProject: Project | null;
  controls: TemplateControls;
  generatedContent: string;
  isGenerating: boolean;
  currentView: 'dashboard' | 'templates' | 'editor';
  phase: StudioPhase;
  chatRequest: string;
  chatMessages: ChatMessage[];
  templateSuggestions: SuggestedTemplate[];
  selectedSuggestedTemplateId: string | null;
  suggestionFallbackToManual: boolean;
}
