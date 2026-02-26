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

export interface AppState {
  projects: Project[];
  templates: Template[];
  selectedTemplate: Template | null;
  currentProject: Project | null;
  controls: TemplateControls;
  generatedContent: string;
  isGenerating: boolean;
  currentView: 'dashboard' | 'templates' | 'editor';
}
