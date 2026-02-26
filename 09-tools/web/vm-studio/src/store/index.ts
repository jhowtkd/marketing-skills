import { create } from 'zustand';
import { createJSONStorage, persist, type StateStorage } from 'zustand/middleware';
import type { AppState, ChatMessage, Project, StudioPhase, SuggestedTemplate, Template, TemplateControls } from '../types';

const INITIAL_TEMPLATES: Template[] = [
  {
    id: 'plan-launch-90d',
    name: 'Plano de Lançamento 90 dias',
    description: 'Estratégia completa para lançar um produto digital B2B com calendário, emails e conteúdo social.',
    tags: ['B2B', 'Lançamento', 'Estratégia'],
    estimatedTime: '10 min',
    parameters: [
      { id: 'productName', type: 'text', label: 'Nome do produto', placeholder: 'Ex: CRM Pro' },
      { id: 'audience', type: 'text', label: 'Público-alvo', placeholder: 'Ex: Clínicas médicas' },
      { id: 'tone', type: 'slider', label: 'Tom de voz', min: 0, max: 100, defaultValue: 50 },
      {
        id: 'focus',
        type: 'select',
        label: 'Foco principal',
        options: [
          { value: 'awareness', label: 'Awareness' },
          { value: 'conversion', label: 'Conversão' },
          { value: 'retention', label: 'Retenção' },
        ],
      },
    ],
  },
  {
    id: 'landing-conversion',
    name: 'Landing Page de Conversão',
    description: 'Copy completa para página de captura ou venda, com hero, problema, solução e CTA.',
    tags: ['Landing Page', 'Copy', 'Conversão'],
    estimatedTime: '5 min',
    parameters: [
      { id: 'productName', type: 'text', label: 'Nome do produto/serviço', placeholder: 'Ex: Consultoria SEO' },
      {
        id: 'problem',
        type: 'textarea',
        label: 'Problema que resolve',
        placeholder: 'Ex: Sites que não aparecem no Google',
      },
      {
        id: 'solution',
        type: 'textarea',
        label: 'Solução oferecida',
        placeholder: 'Ex: Otimização completa para ranquear',
      },
      { id: 'tone', type: 'slider', label: 'Tom emocional → Racional', min: 0, max: 100, defaultValue: 50 },
    ],
  },
  {
    id: 'email-nurture',
    name: 'Sequência de Emails Nurture',
    description: 'Série de emails para nutrir leads desde o primeiro contato até a conversão.',
    tags: ['Email', 'Nurture', 'Automação'],
    estimatedTime: '7 min',
    parameters: [
      {
        id: 'context',
        type: 'select',
        label: 'Contexto do lead',
        options: [
          { value: 'trial', label: 'Trial grátis' },
          { value: 'lead-magnet', label: 'Baixou lead magnet' },
          { value: 'webinar', label: 'Participou de webinar' },
        ],
      },
      {
        id: 'emailCount',
        type: 'select',
        label: 'Número de emails',
        options: [
          { value: '3', label: '3 emails' },
          { value: '5', label: '5 emails' },
          { value: '7', label: '7 emails' },
        ],
      },
      { id: 'tone', type: 'slider', label: 'Pessoal → Institucional', min: 0, max: 100, defaultValue: 30 },
    ],
  },
];

interface StoreActions {
  setView: (view: AppState['currentView']) => void;
  selectTemplate: (template: Template | null) => void;
  setControl: (key: string, value: string | number) => void;
  createProject: (name: string) => Project;
  loadProject: (project: Project) => void;
  setGeneratedContent: (content: string) => void;
  setIsGenerating: (isGenerating: boolean) => void;
  updateProject: (projectId: string, updates: Partial<Project>) => void;
  deleteProject: (projectId: string) => void;
  startFromChatRequest: (requestText: string) => void;
  setTemplateSuggestions: (suggestions: SuggestedTemplate[]) => void;
  chooseSuggestedTemplate: (templateId: string) => void;
  setPhase: (phase: StudioPhase) => void;
  appendChatMessage: (message: ChatMessage) => void;
}

const getDefaultControls = (template: Template): TemplateControls => {
  const controls: TemplateControls = {};
  template.parameters.forEach((p) => {
    controls[p.id] = p.defaultValue ?? (p.type === 'slider' ? 50 : '');
  });
  return controls;
};

const NOOP_STORAGE: StateStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

const getPersistStorage = (): StateStorage => {
  const candidate = (globalThis as { localStorage?: Partial<StateStorage> }).localStorage;
  if (
    candidate &&
    typeof candidate.getItem === 'function' &&
    typeof candidate.setItem === 'function' &&
    typeof candidate.removeItem === 'function'
  ) {
    return candidate as StateStorage;
  }
  return NOOP_STORAGE;
};

export const useStore = create<AppState & StoreActions>()(
  persist(
    (set, get) => ({
      projects: [],
      templates: INITIAL_TEMPLATES,
      selectedTemplate: null,
      currentProject: null,
      controls: {},
      generatedContent: '',
      isGenerating: false,
      currentView: 'dashboard',
      phase: 'chat_input',
      chatRequest: '',
      chatMessages: [],
      templateSuggestions: [],
      selectedSuggestedTemplateId: null,
      suggestionFallbackToManual: false,

      setView: (view) => set({ currentView: view }),

      selectTemplate: (template) =>
        set({
          selectedTemplate: template,
          controls: template ? getDefaultControls(template) : {},
          generatedContent: '',
        }),

      setControl: (key, value) =>
        set((state) => ({
          controls: { ...state.controls, [key]: value },
        })),

      createProject: (name) => {
        const template = get().selectedTemplate!;
        const project: Project = {
          id: `proj-${Date.now()}`,
          name,
          templateId: template.id,
          templateName: template.name,
          status: 'draft',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        set((state) => ({
          projects: [project, ...state.projects],
          currentProject: project,
          currentView: 'editor',
        }));
        return project;
      },

      loadProject: (project) => {
        const template = get().templates.find((t) => t.id === project.templateId);
        set({
          currentProject: project,
          selectedTemplate: template || null,
          controls: template ? getDefaultControls(template) : {},
          generatedContent: project.content || '',
          currentView: 'editor',
        });
      },

      setGeneratedContent: (content) => set({ generatedContent: content }),
      setIsGenerating: (isGenerating) => set({ isGenerating }),

      updateProject: (projectId, updates) =>
        set((state) => ({
          projects: state.projects.map((p) =>
            p.id === projectId ? { ...p, ...updates, updatedAt: new Date().toISOString() } : p
          ),
          currentProject:
            state.currentProject?.id === projectId
              ? { ...state.currentProject, ...updates, updatedAt: new Date().toISOString() }
              : state.currentProject,
        })),

      deleteProject: (projectId) =>
        set((state) => ({
          projects: state.projects.filter((p) => p.id !== projectId),
          currentProject: state.currentProject?.id === projectId ? null : state.currentProject,
        })),

      startFromChatRequest: (requestText) => {
        const trimmedRequest = requestText.trim();
        const requestMessage: ChatMessage = {
          id: `msg-${Date.now()}`,
          role: 'user',
          content: trimmedRequest,
          createdAt: new Date().toISOString(),
        };
        set((state) => ({
          chatRequest: trimmedRequest,
          chatMessages: [...state.chatMessages, requestMessage],
          templateSuggestions: [],
          selectedSuggestedTemplateId: null,
          suggestionFallbackToManual: false,
          phase: 'template_suggestion',
        }));
      },

      setTemplateSuggestions: (suggestions) =>
        set({
          templateSuggestions: suggestions.slice(0, 3),
          suggestionFallbackToManual: suggestions.length === 0,
        }),

      chooseSuggestedTemplate: (templateId) =>
        set((state) => {
          const template = state.templates.find((item) => item.id === templateId) || null;
          if (!template) {
            return {
              selectedSuggestedTemplateId: null,
              suggestionFallbackToManual: true,
            };
          }
          return {
            selectedSuggestedTemplateId: templateId,
            selectedTemplate: template,
            controls: getDefaultControls(template),
            suggestionFallbackToManual: false,
            phase: 'generating',
            currentView: 'editor',
          };
        }),

      setPhase: (phase) => set({ phase }),

      appendChatMessage: (message) =>
        set((state) => ({
          chatMessages: [...state.chatMessages, message],
        })),
    }),
    {
      name: 'vm-studio-storage',
      storage: createJSONStorage(getPersistStorage),
      partialize: (state) => ({ projects: state.projects }),
    }
  )
);
