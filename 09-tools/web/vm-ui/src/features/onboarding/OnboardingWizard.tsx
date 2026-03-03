import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  trackOnboardingStarted,
  trackOnboardingCompleted,
  OnboardingStep,
} from './telemetry';
import { saveFunnelState, loadFunnelState, getNextStep } from './funnel';
import { ContextualTour } from './ContextualTour';
import type { TourStep } from './ContextualTour';

// v38: Smart prefill integration
interface PrefillData {
  fields: Record<string, string>;
  source: string;
  confidence: string;
}

const fetchPrefillData = async (userId: string): Promise<PrefillData | null> => {
  try {
    // Parse UTM params from URL
    const urlParams = new URLSearchParams(window.location.search);
    const utmCampaign = urlParams.get('utm_campaign') || undefined;
    const utmSource = urlParams.get('utm_source') || undefined;
    const utmMedium = urlParams.get('utm_medium') || undefined;
    
    // Get referrer
    const referrer = document.referrer || undefined;
    
    const response = await fetch('/api/v2/onboarding/prefill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        utm_campaign: utmCampaign,
        utm_source: utmSource,
        utm_medium: utmMedium,
        referrer,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    return {
      fields: data.fields || {},
      source: data.prefill_source,
      confidence: data.confidence,
    };
  } catch (error) {
    console.warn('Failed to fetch prefill data:', error);
    return null;
  }
};

export { OnboardingStep };

interface OnboardingWizardProps {
  userId: string;
  onComplete: () => void;
  onSkip: () => void;
}

interface WizardState {
  currentStep: OnboardingStep;
  workspaceName: string;
  selectedTemplate: string | null;
  startedAt: number;
}

// v38: Track which fields have been explicitly modified by user
interface ExplicitFields {
  workspaceName: boolean;
  selectedTemplate: boolean;
}

const TOTAL_STEPS = 5;

const STEP_ORDER: OnboardingStep[] = [
  OnboardingStep.WELCOME,
  OnboardingStep.WORKSPACE_SETUP,
  OnboardingStep.TEMPLATE_SELECTION,
  OnboardingStep.CUSTOMIZATION,
  OnboardingStep.COMPLETION,
];

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({
  userId,
  onComplete,
  onSkip,
}) => {
  const [state, setState] = useState<WizardState>({
    currentStep: OnboardingStep.WELCOME,
    workspaceName: '',
    selectedTemplate: null,
    startedAt: Date.now(),
  });

  // v38: Prefill state
  const [prefill, setPrefill] = useState<PrefillData | null>(null);
  const [explicitFields, setExplicitFields] = useState<ExplicitFields>({
    workspaceName: false,
    selectedTemplate: false,
  });
  const [prefillApplied, setPrefillApplied] = useState(false);
  
  // Refs to track if prefill fetch is in progress
  const prefillFetchedRef = useRef(false);

  // v30: Contextual tour state
  const [showTour, setShowTour] = useState(false);

  // Tour steps for contextual guidance
  const tourSteps: TourStep[] = [
    {
      id: 'welcome',
      title: 'Bem-vindo ao VM Studio',
      content: 'Vamos guiar você pelos primeiros passos para criar seu primeiro conteúdo.',
      target: '#wizard-welcome',
    },
    {
      id: 'workspace',
      title: 'Configure seu Workspace',
      content: 'Dê um nome ao seu workspace para organizar seus projetos.',
      target: '#wizard-workspace',
    },
    {
      id: 'templates',
      title: 'Escolha um Template',
      content: 'Selecione um template pré-configurado para acelerar seu trabalho.',
      target: '#wizard-templates',
    },
    {
      id: 'completion',
      title: 'Pronto para começar!',
      content: 'Seu setup está completo. Vamos criar algo incrível juntos.',
      target: '#wizard-completion',
    },
  ];

  useEffect(() => {
    trackOnboardingStarted(userId);
  }, [userId]);

  // v38: Fetch and apply smart prefill
  useEffect(() => {
    if (prefillFetchedRef.current) return;
    prefillFetchedRef.current = true;

    const loadPrefill = async () => {
      const prefillData = await fetchPrefillData(userId);
      if (prefillData) {
        setPrefill(prefillData);
        
        // Apply prefill only for fields not explicitly set by user
        setState((prev) => {
          const updates: Partial<WizardState> = {};
          
          // Apply template prefill if not explicitly selected
          if (!explicitFields.selectedTemplate && prefillData.fields.template_id) {
            updates.selectedTemplate = prefillData.fields.template_id;
          }
          
          return { ...prev, ...updates };
        });
        
        setPrefillApplied(true);
      }
    };

    loadPrefill();
  }, [userId, explicitFields.selectedTemplate]);

  useEffect(() => {
    saveFunnelState({
      userId,
      currentStep: state.currentStep,
      startedAt: new Date(state.startedAt),
      completedSteps: STEP_ORDER.slice(0, STEP_ORDER.indexOf(state.currentStep)),
      lastActivityAt: new Date(),
    });
  }, [state.currentStep, userId, state.startedAt]);

  const currentStepIndex = STEP_ORDER.indexOf(state.currentStep);
  const progress = ((currentStepIndex + 1) / TOTAL_STEPS) * 100;

  const canContinue = useCallback(() => {
    switch (state.currentStep) {
      case OnboardingStep.WORKSPACE_SETUP:
        return state.workspaceName.trim().length > 0;
      case OnboardingStep.TEMPLATE_SELECTION:
        return state.selectedTemplate !== null;
      default:
        return true;
    }
  }, [state.currentStep, state.workspaceName, state.selectedTemplate]);

  const handleNext = useCallback(() => {
    const nextStep = getNextStep(state.currentStep);
    if (nextStep) {
      setState((prev) => ({ ...prev, currentStep: nextStep as OnboardingStep }));
    }
  }, [state.currentStep]);

  const handleBack = useCallback(() => {
    const currentIndex = STEP_ORDER.indexOf(state.currentStep);
    if (currentIndex > 0) {
      setState((prev) => ({
        ...prev,
        currentStep: STEP_ORDER[currentIndex - 1],
      }));
    }
  }, [state.currentStep]);

  const handleFinish = useCallback(() => {
    const durationMs = Date.now() - state.startedAt;
    trackOnboardingCompleted(userId, durationMs);
    onComplete();
  }, [onComplete, state.startedAt, userId]);

  const handleWorkspaceNameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setExplicitFields((prev) => ({ ...prev, workspaceName: true }));
      setState((prev) => ({ ...prev, workspaceName: e.target.value }));
    },
    []
  );

  const handleTemplateSelect = useCallback((templateId: string) => {
    setExplicitFields((prev) => ({ ...prev, selectedTemplate: true }));
    setState((prev) => ({ ...prev, selectedTemplate: templateId }));
  }, []);

  const renderStep = () => {
    switch (state.currentStep) {
      case OnboardingStep.WELCOME:
        return (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold text-gray-900">
              Bem-vindo ao VM Studio
            </h1>
            <p className="text-gray-600">
              Vamos configurar seu workspace em poucos passos simples.
            </p>
          </div>
        );

      case OnboardingStep.WORKSPACE_SETUP:
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Configurar Workspace
            </h2>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nome do Workspace
              </label>
              <input
                type="text"
                placeholder="Nome do workspace"
                value={state.workspaceName}
                onChange={handleWorkspaceNameChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        );

      case OnboardingStep.TEMPLATE_SELECTION:
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                Escolha um Template
              </h2>
              {/* v38: Prefill indicator */}
              {prefillApplied && prefill?.fields.template_id && !explicitFields.selectedTemplate && (
                <span 
                  className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded-full"
                  data-testid="prefill-indicator"
                >
                  Sugerido ✨
                </span>
              )}
            </div>
            <p className="text-gray-600">
              Selecione um template para começar rápido:
              {prefillApplied && prefill?.confidence === 'high' && (
                <span className="block text-sm text-green-600 mt-1">
                  Detectamos que você veio de uma campanha de {prefill.fields.template_id?.replace('-', ' ') || 'conteúdo'}.
                </span>
              )}
            </p>
            <div className="grid grid-cols-2 gap-3">
              {['blog-post', 'landing-page', 'social-media', 'email'].map(
                (template) => (
                  <button
                    key={template}
                    onClick={() => handleTemplateSelect(template)}
                    className={`p-4 border rounded-lg text-left transition-colors ${
                      state.selectedTemplate === template
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    data-testid={`template-${template}`}
                  >
                    <span className="font-medium capitalize">
                      {template.replace('-', ' ')}
                    </span>
                  </button>
                )
              )}
            </div>
          </div>
        );

      case OnboardingStep.CUSTOMIZATION:
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Personalização
            </h2>
            <p className="text-gray-600">
              Quase lá! Suas configurações foram salvas.
            </p>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-sm text-gray-700">
                <strong>Workspace:</strong> {state.workspaceName}
              </p>
              <p className="text-sm text-gray-700">
                <strong>Template:</strong>{' '}
                {state.selectedTemplate?.replace('-', ' ') || 'Nenhum'}
              </p>
            </div>
          </div>
        );

      case OnboardingStep.COMPLETION:
        return (
          <div className="space-y-4 text-center">
            <div className="text-5xl mb-4">🎉</div>
            <h2 className="text-xl font-semibold text-gray-900">
              Configuração Concluída!
            </h2>
            <p className="text-gray-600">
              Seu workspace está pronto. Vamos criar algo incrível!
            </p>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="max-w-md mx-auto bg-white rounded-lg shadow-lg p-6">
      {/* Progress */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">
            Passo {currentStepIndex + 1} de {TOTAL_STEPS}
          </span>
          <span className="text-sm text-gray-500">{Math.round(progress)}%</span>
        </div>
        <div
          className="w-full bg-gray-200 rounded-full h-2"
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Step Content */}
      <div className="mb-8">{renderStep()}</div>

      {/* Actions */}
      <div className="flex justify-between items-center">
        <div>
          {currentStepIndex > 0 && (
            <button
              onClick={handleBack}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Voltar
            </button>
          )}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onSkip}
            className="px-4 py-2 text-gray-500 hover:text-gray-700 transition-colors"
          >
            Pular
          </button>

          {state.currentStep === OnboardingStep.COMPLETION ? (
            <button
              onClick={handleFinish}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Começar a Usar
            </button>
          ) : (
            <button
              onClick={handleNext}
              disabled={!canContinue()}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              Continuar
            </button>
          )}
        </div>
      </div>

      {/* v30: Contextual Tour Integration */}
      <ContextualTour
        steps={tourSteps}
        isOpen={showTour}
        onComplete={() => setShowTour(false)}
        onSkip={() => setShowTour(false)}
        tourId={`onboarding-${userId}`}
      />
    </div>
  );
};
