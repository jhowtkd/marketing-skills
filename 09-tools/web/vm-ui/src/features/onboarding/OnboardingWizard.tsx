import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  trackOnboardingStarted,
  trackOnboardingCompleted,
  OnboardingStep,
} from './telemetry';
import {
  trackFastLanePresented,
  trackFastLaneAccepted,
  trackFastLaneRejected,
  trackOnboardingProgressSaved,
  trackOnboardingResumePresented,
  trackOnboardingResumeAccepted,
  trackOnboardingResumeRejected,
  trackOnboardingResumeFailed,
} from './ttfvTelemetry';
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

// v38: Fast lane integration
interface FastLaneData {
  isFastLane: boolean;
  skippedSteps: string[];
  remainingSteps: string[];
  estimatedTimeSavedMinutes: number;
  justification?: string;
}

const fetchFastLaneData = async (
  userId: string,
  checklist: Record<string, boolean>
): Promise<FastLaneData | null> => {
  try {
    const response = await fetch('/api/v2/onboarding/fast-lane', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        checklist,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    return {
      isFastLane: data.is_fast_lane,
      skippedSteps: data.skipped_steps || [],
      remainingSteps: data.remaining_steps || [],
      estimatedTimeSavedMinutes: data.estimated_time_saved_minutes || 0,
      justification: data.justification,
    };
  } catch (error) {
    console.warn('Failed to fetch fast lane data:', error);
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
  OnboardingStep.TEMPLATE_SELECTION,
  OnboardingStep.WORKSPACE_SETUP,
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
  
  // v38: Fast lane state
  const [fastLane, setFastLane] = useState<FastLaneData | null>(null);
  const [fastLaneChecklist, setFastLaneChecklist] = useState({
    terms_accepted: true,  // Assumed accepted to proceed
    email_verified: true,  // Assumed verified
    privacy_policy: true,  // Assumed accepted
  });
  
  // v39: Fast lane recommendation offer state
  const [fastLaneOffer, setFastLaneOffer] = useState<{
    recommendedPath: 'fast_lane' | 'standard';
    confidence: number;
    reasons: string[];
    skippedSteps: string[];
    estimatedTimeSavedMinutes: number;
  } | null>(null);
  
  // v39: Track if fast lane offer has been presented
  const fastLanePresentedRef = useRef(false);
  
  // Refs to track if fetches are in progress
  const prefillFetchedRef = useRef(false);
  const fastLaneFetchedRef = useRef(false);
  const progressCheckedRef = useRef(false);
  
  // v40: Save/Resume state
  const [savedProgress, setSavedProgress] = useState<{
    hasProgress: boolean;
    lastStep: string;
    lastUpdated: string;
    stepData: Record<string, any>;
    completedSteps: string[];
  } | null>(null);
  
  const [showResumePrompt, setShowResumePrompt] = useState(false);
  const [isResuming, setIsResuming] = useState(false);

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
  
  // v40: Check for saved progress on mount
  useEffect(() => {
    if (progressCheckedRef.current) return;
    progressCheckedRef.current = true;
    
    const checkSavedProgress = async () => {
      try {
        const response = await fetch(`/api/v2/onboarding/progress/${userId}`);
        if (response.ok) {
          const data = await response.json();
          if (data.has_progress) {
            setSavedProgress({
              hasProgress: data.has_progress,
              lastStep: data.current_step,
              lastUpdated: data.updated_at,
              stepData: data.step_data || {},
              completedSteps: data.completed_steps || [],
            });
            setShowResumePrompt(true);
            trackOnboardingResumePresented(userId, data.current_step);
          }
        }
      } catch (error) {
        console.warn('Failed to check saved progress:', error);
      }
    };
    
    checkSavedProgress();
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

  // v38: Fetch fast lane configuration
  useEffect(() => {
    if (fastLaneFetchedRef.current) return;
    fastLaneFetchedRef.current = true;

    const loadFastLane = async () => {
      const fastLaneData = await fetchFastLaneData(userId, fastLaneChecklist);
      if (fastLaneData) {
        setFastLane(fastLaneData);
      }
    };

    loadFastLane();
  }, [userId, fastLaneChecklist]);
  
  // v39: Fetch fast lane recommendation
  const fetchFastLaneRecommendation = useCallback(async (
    userChecklist: Record<string, boolean>,
    userContext?: { utmSource?: string; referrer?: string }
  ) => {
    try {
      const response = await fetch('/api/v2/onboarding/fast-lane-recommendation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          checklist: userChecklist,
          context: userContext,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      return {
        recommendedPath: data.recommended_path as 'fast_lane' | 'standard',
        confidence: data.confidence || 0,
        reasons: data.reasons || [],
        skippedSteps: data.skipped_steps || [],
        estimatedTimeSavedMinutes: data.estimated_time_saved_minutes || 0,
      };
    } catch (error) {
      console.warn('Failed to fetch fast lane recommendation:', error);
      return null;
    }
  }, [userId]);
  
  // v39: Load fast lane recommendation on mount
  useEffect(() => {
    if (fastLanePresentedRef.current) return;
    
    const loadRecommendation = async () => {
      const recommendation = await fetchFastLaneRecommendation(fastLaneChecklist);
      if (recommendation && recommendation.recommendedPath === 'fast_lane') {
        setFastLaneOffer(recommendation);
        // Track that fast lane was presented
        await trackFastLanePresented(
          userId,
          recommendation.confidence,
          recommendation.recommendedPath,
          recommendation.estimatedTimeSavedMinutes,
          recommendation.skippedSteps,
          recommendation.reasons
        );
        fastLanePresentedRef.current = true;
      }
    };
    
    loadRecommendation();
  }, [userId, fastLaneChecklist, fetchFastLaneRecommendation]);
  
  // v39: Handler for accepting fast lane
  const handleAcceptFastLane = useCallback(async () => {
    if (!fastLaneOffer) return;
    
    await trackFastLaneAccepted(
      userId,
      fastLaneOffer.confidence,
      fastLaneOffer.estimatedTimeSavedMinutes,
      fastLaneOffer.skippedSteps
    );
    
    // Apply skipped steps by updating fast lane state
    setFastLane({
      isFastLane: true,
      skippedSteps: fastLaneOffer.skippedSteps,
      remainingSteps: STEP_ORDER.filter(s => !fastLaneOffer.skippedSteps.includes(s)),
      estimatedTimeSavedMinutes: fastLaneOffer.estimatedTimeSavedMinutes,
      justification: 'User accepted fast lane recommendation',
    });
    
    // Clear the offer after accepting
    setFastLaneOffer(null);
  }, [fastLaneOffer, userId]);
  
  // v39: Handler for rejecting fast lane
  const handleRejectFastLane = useCallback(async () => {
    if (!fastLaneOffer) return;
    
    await trackFastLaneRejected(
      userId,
      fastLaneOffer.confidence,
      fastLaneOffer.reasons
    );
    
    // Clear the offer
    setFastLaneOffer(null);
  }, [fastLaneOffer, userId]);

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

  // v40: Auto-save progress when completing a step
  const autoSaveProgress = useCallback(async (step: string, stepData: any) => {
    try {
      const currentCompletedSteps = STEP_ORDER.slice(0, STEP_ORDER.indexOf(step as OnboardingStep));
      await fetch(`/api/v2/onboarding/progress/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_step: step,
          step_data: stepData,
          completed_steps: currentCompletedSteps,
          source: 'auto_save'
        })
      });
      trackOnboardingProgressSaved(userId, step, 'auto_save');
    } catch (error) {
      console.warn('Failed to auto-save progress:', error);
    }
  }, [userId]);

  const handleNext = useCallback(() => {
    const nextStep = getNextStep(state.currentStep);
    if (nextStep) {
      setState((prev) => ({ ...prev, currentStep: nextStep as OnboardingStep }));
      
      // v40: Auto-save progress after advancing step
      autoSaveProgress(nextStep, {
        workspaceName: state.workspaceName,
        selectedTemplate: state.selectedTemplate,
      });
    }
  }, [state.currentStep, state.workspaceName, state.selectedTemplate, autoSaveProgress]);

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
  
  // v40: Handler for accepting resume
  const handleResume = useCallback(async () => {
    if (!savedProgress) return;
    
    trackOnboardingResumeAccepted(userId, savedProgress.lastStep);
    
    // Hydrate state from saved progress
    setState((prev) => ({
      ...prev,
      currentStep: savedProgress.lastStep as OnboardingStep,
      workspaceName: savedProgress.stepData.workspaceName || '',
      selectedTemplate: savedProgress.stepData.selectedTemplate || null,
    }));
    
    setIsResuming(true);
    setShowResumePrompt(false);
  }, [savedProgress, userId]);
  
  // v40: Handler for starting fresh (rejecting resume)
  const handleStartFresh = useCallback(async () => {
    trackOnboardingResumeRejected(userId, 'user_chose_fresh_start');
    
    try {
      await fetch(`/api/v2/onboarding/progress/${userId}`, { method: 'DELETE' });
    } catch (error) {
      console.warn('Failed to clear saved progress:', error);
    }
    
    setShowResumePrompt(false);
    // Reset wizard to initial state
    setState({
      currentStep: OnboardingStep.WELCOME,
      workspaceName: '',
      selectedTemplate: null,
      startedAt: Date.now(),
    });
    setIsResuming(false);
  }, [userId]);
  
  // v40: Reset isResuming after state is hydrated
  useEffect(() => {
    if (isResuming) {
      setIsResuming(false);
    }
  }, [isResuming]);

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
            {/* v39: Fast lane CTA offer */}
            {fastLaneOffer && (
              <div 
                className="mt-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg"
                data-testid="fast-lane-cta"
              >
                <div className="flex items-start gap-3">
                  <div className="text-3xl">🚀</div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-blue-900">
                      Caminho Recomendado Disponível!
                    </h3>
                    <p className="text-sm text-blue-700 mt-1">
                      Baseado no seu perfil, temos um caminho otimizado que economiza 
                      <span className="font-semibold"> {fastLaneOffer.estimatedTimeSavedMinutes} minutos</span>.
                    </p>
                    {fastLaneOffer.reasons.length > 0 && (
                      <ul className="text-xs text-blue-600 mt-2 space-y-1">
                        {fastLaneOffer.reasons.map((reason, idx) => (
                          <li key={idx} className="flex items-center gap-1">
                            <span>✓</span> {reason}
                          </li>
                        ))}
                      </ul>
                    )}
                    {fastLaneOffer.skippedSteps.length > 0 && (
                      <p className="text-xs text-blue-600 mt-2">
                        Etapas puladas: {fastLaneOffer.skippedSteps.join(', ')}
                      </p>
                    )}
                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={handleAcceptFastLane}
                        className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
                        data-testid="fast-lane-accept"
                      >
                        Usar caminho recomendado
                      </button>
                      <button
                        onClick={handleRejectFastLane}
                        className="px-4 py-2 bg-white text-blue-600 text-sm font-medium border border-blue-300 rounded-md hover:bg-blue-50 transition-colors"
                        data-testid="fast-lane-reject"
                      >
                        Não, obrigado
                      </button>
                    </div>
                    <p className="text-xs text-blue-500 mt-2">
                      Confiança da recomendação: {Math.round(fastLaneOffer.confidence * 100)}%
                    </p>
                  </div>
                </div>
              </div>
            )}
            {/* v38: Fast lane indicator */}
            {fastLane?.isFastLane && !fastLaneOffer && (
              <div 
                className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg"
                data-testid="fast-lane-badge"
              >
                <p className="text-sm text-green-800">
                  <span className="font-medium">🚀 Fast Lane ativado!</span>
                  <br />
                  Você foi selecionado para um onboarding acelerado.
                  {fastLane.estimatedTimeSavedMinutes > 0 && (
                    <span> Economize até {fastLane.estimatedTimeSavedMinutes} minutos.</span>
                  )}
                </p>
              </div>
            )}
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
        // v38: Check if this step should be skipped due to fast lane
        const shouldSkipCustomization = fastLane?.isFastLane && 
          fastLane.skippedSteps.includes('customization');
        
        if (shouldSkipCustomization) {
          // Auto-advance to next step after a brief delay
          setTimeout(() => handleNext(), 100);
        }
        
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                Personalização
              </h2>
              {fastLane?.isFastLane && (
                <span 
                  className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded-full"
                  data-testid="fast-lane-skip-indicator"
                >
                  Pulado (Fast Lane)
                </span>
              )}
            </div>
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

      {/* Resume Prompt */}
      {showResumePrompt && savedProgress?.hasProgress && (
        <div 
          data-testid="resume-prompt"
          className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg"
        >
          <div className="flex items-start gap-3">
            <span className="text-2xl">🔄</span>
            <div className="flex-1">
              <h3 className="font-semibold text-amber-900 mb-1">
                Retomar de onde parou?
              </h3>
              <p className="text-sm text-amber-700 mb-2">
                Você tem progresso salvo na etapa: <strong>{savedProgress.lastStep.replace(/_/g, ' ')}</strong>
                <br />
                <span className="text-xs">
                  Última atualização: {new Date(savedProgress.lastUpdated).toLocaleString('pt-BR')}
                </span>
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleResume}
                  className="px-4 py-2 bg-amber-600 text-white text-sm rounded-md hover:bg-amber-700 transition-colors"
                  data-testid="resume-accept"
                >
                  Retomar progresso
                </button>
                <button
                  onClick={handleStartFresh}
                  className="px-4 py-2 bg-white text-amber-700 border border-amber-300 text-sm rounded-md hover:bg-amber-50 transition-colors"
                  data-testid="resume-reject"
                >
                  Começar do zero
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
