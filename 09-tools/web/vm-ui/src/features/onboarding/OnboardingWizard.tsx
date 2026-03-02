import React, { useState, useCallback, useEffect } from 'react';
import {
  trackOnboardingStarted,
  trackOnboardingCompleted,
  OnboardingStep,
} from './telemetry';
import { saveFunnelState, loadFunnelState, getNextStep } from './funnel';

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

  useEffect(() => {
    trackOnboardingStarted(userId);
  }, [userId]);

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
      setState((prev) => ({ ...prev, workspaceName: e.target.value }));
    },
    []
  );

  const handleTemplateSelect = useCallback((templateId: string) => {
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
            <h2 className="text-xl font-semibold text-gray-900">
              Escolha um Template
            </h2>
            <p className="text-gray-600">
              Selecione um template para começar rápido:
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
    </div>
  );
};
