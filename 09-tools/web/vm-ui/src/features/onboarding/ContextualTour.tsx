import React, { useState, useEffect, useCallback, useMemo } from 'react';

export interface TourStep {
  id: string;
  title: string;
  content: string;
  target: string;
}

interface ContextualTourProps {
  steps: TourStep[];
  isOpen: boolean;
  onComplete: () => void;
  onSkip: () => void;
  resumeStepId?: string | null;
  tourId?: string;
}

const STORAGE_KEY_PREFIX = 'vm_tour_';

export const ContextualTour: React.FC<ContextualTourProps> = ({
  steps,
  isOpen,
  onComplete,
  onSkip,
  resumeStepId,
  tourId,
}) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  // Initialize from resume state or saved progress
  useEffect(() => {
    if (!isOpen) return;

    if (resumeStepId) {
      const stepIndex = steps.findIndex((s) => s.id === resumeStepId);
      if (stepIndex >= 0) {
        setCurrentStepIndex(stepIndex);
      }
    } else if (tourId) {
      try {
        const saved = localStorage.getItem(`${STORAGE_KEY_PREFIX}${tourId}_progress`);
        if (saved) {
          const { stepId } = JSON.parse(saved);
          const stepIndex = steps.findIndex((s) => s.id === stepId);
          if (stepIndex >= 0) {
            setCurrentStepIndex(stepIndex);
          }
        }
      } catch {
        // Ignore storage errors
      }
    }
  }, [isOpen, resumeStepId, steps, tourId]);

  // Persist progress on step change
  useEffect(() => {
    if (!isOpen || !tourId) return;

    try {
      const currentStep = steps[currentStepIndex];
      if (currentStep) {
        localStorage.setItem(
          `${STORAGE_KEY_PREFIX}${tourId}_progress`,
          JSON.stringify({ stepId: currentStep.id, timestamp: Date.now() })
        );
      }
    } catch {
      // Ignore storage errors
    }
  }, [currentStepIndex, isOpen, steps, tourId]);

  const currentStep = steps[currentStepIndex];
  const progress = ((currentStepIndex + 1) / steps.length) * 100;
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === steps.length - 1;

  const handleNext = useCallback(() => {
    if (isLastStep) {
      // Clear progress on complete
      if (tourId) {
        try {
          localStorage.removeItem(`${STORAGE_KEY_PREFIX}${tourId}_progress`);
        } catch {
          // Ignore storage errors
        }
      }
      onComplete();
    } else {
      setCurrentStepIndex((prev) => Math.min(prev + 1, steps.length - 1));
    }
  }, [isLastStep, onComplete, steps.length, tourId]);

  const handleBack = useCallback(() => {
    setCurrentStepIndex((prev) => Math.max(prev - 1, 0));
  }, []);

  const handleSkip = useCallback(() => {
    // Save current progress before skipping
    if (tourId && currentStep) {
      try {
        localStorage.setItem(
          `${STORAGE_KEY_PREFIX}${tourId}_progress`,
          JSON.stringify({ stepId: currentStep.id, timestamp: Date.now() })
        );
      } catch {
        // Ignore storage errors
      }
    }
    onSkip();
  }, [currentStep, onSkip, tourId]);

  // Position calculation (simplified - would use actual target element positioning in real implementation)
  const position = useMemo(() => {
    return { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' };
  }, []);

  if (!isOpen || !currentStep) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-40 bg-black/30"
        onClick={handleSkip}
        data-testid="tour-overlay"
      />

      {/* Tour Card */}
      <div
        className="fixed z-50 w-full max-w-md bg-white rounded-lg shadow-2xl p-6"
        style={position}
      >
        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">
              Passo {currentStepIndex + 1} de {steps.length}
            </span>
            <span className="text-xs text-gray-500">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Step Content */}
        <div className="mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            {currentStep.title}
          </h3>
          <p className="text-gray-600">{currentStep.content}</p>
        </div>

        {/* Actions */}
        <div className="flex justify-between items-center">
          <button
            onClick={handleBack}
            disabled={isFirstStep}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Anterior
          </button>

          <button
            onClick={handleSkip}
            className="px-4 py-2 text-gray-500 hover:text-gray-700 transition-colors"
          >
            Pular tour
          </button>

          <button
            onClick={handleNext}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            {isLastStep ? 'Finalizar' : 'Próximo'}
          </button>
        </div>

        {/* Dots Indicator */}
        <div className="flex justify-center gap-2 mt-4">
          {steps.map((_, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full transition-colors ${
                index === currentStepIndex
                  ? 'bg-blue-600'
                  : index < currentStepIndex
                  ? 'bg-blue-300'
                  : 'bg-gray-300'
              }`}
            />
          ))}
        </div>
      </div>
    </>
  );
};

export default ContextualTour;
