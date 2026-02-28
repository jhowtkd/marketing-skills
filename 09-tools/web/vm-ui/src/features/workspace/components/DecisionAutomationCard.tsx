/**
 * DecisionAutomationCard.tsx
 * 
 * Card "Automação de Decisão" para o Control Center.
 * 
 * Features:
 * - Status do safety gate
 * - Preview dry-run
 * - Botão "Executar com safety gates"
 * - Badge "Canary ativo"
 */

import React from 'react';
import { useDecisionAutomation } from '../hooks/useDecisionAutomation';

interface DecisionAutomationCardProps {
  segmentKey: string;
}

export const DecisionAutomationCard: React.FC<DecisionAutomationCardProps> = ({
  segmentKey,
}) => {
  const {
    status,
    safetyStatus,
    canaryActive,
    canaryStatus,
    canaryResult,
    preview,
    rollbackInfo,
    isLoading,
    simulate,
    execute,
  } = useDecisionAutomation(segmentKey);

  const getSafetyStatusClass = () => {
    if (!safetyStatus) return '';
    if (safetyStatus.allowed) return 'status-ok';
    if (safetyStatus.riskLevel === 'medium') return 'status-warning';
    return 'status-error';
  };

  const getSafetyStatusText = () => {
    if (!safetyStatus) return 'Safety Gates: Verificando...';
    if (safetyStatus.allowed) return 'Safety Gates: OK';
    return 'Safety Gates: Bloqueado';
  };

  const getBlockedReason = () => {
    if (!safetyStatus || safetyStatus.allowed) return null;
    const reasonMap: Record<string, string> = {
      insufficient_sample_size: 'Amostra insuficiente',
      confidence_below_threshold: 'Confiança baixa',
      regression_detected: 'Regressão detectada',
      cooldown_active: 'Aguardar cooldown',
      max_actions_per_day: 'Limite diário atingido',
    };
    return reasonMap[safetyStatus.blockedBy[0]] || safetyStatus.blockedBy[0];
  };

  return (
    <div className="decision-automation-card" data-testid="decision-automation-card">
      <div className="card-header">
        <h3>Automação de Decisão</h3>
        <span className="segment-key">{segmentKey}</span>
        {canaryActive && (
          <span className="badge canary-badge">Canary Ativo</span>
        )}
      </div>

      <div className="card-body">
        {/* Safety Gate Status */}
        <div className="safety-status" data-testid="safety-status">
          <div className={`status-indicator ${getSafetyStatusClass()}`}>
            {getSafetyStatusText()}
          </div>
          {safetyStatus && !safetyStatus.allowed && (
            <div className="blocked-reasons">
              <span className="reason">{getBlockedReason()}</span>
              {safetyStatus.blockedBy.map((reason) => (
                <span key={reason} className="block-code">{reason}</span>
              ))}
            </div>
          )}
        </div>

        {/* Canary Status */}
        {canaryActive && canaryStatus && (
          <div className="canary-status">
            <span className="badge">Canary Ativo</span>
            <span className="subset-info">{canaryStatus.subsetPercentage}% subset</span>
            <span className="time-info">{canaryStatus.observationTimeRemaining} min restantes</span>
          </div>
        )}

        {status === 'canary_promoted' && canaryResult && (
          <div className="canary-result success">
            <span>Canary Promovido</span>
            <span>{Math.round(canaryResult.successRate * 100)}% sucesso</span>
          </div>
        )}

        {status === 'canary_aborted' && canaryResult && (
          <div className="canary-result error">
            <span>Canary Abortado</span>
            <span>{Math.round(canaryResult.successRate * 100)}% sucesso - abaixo do threshold</span>
          </div>
        )}

        {/* Preview */}
        {preview && (
          <div className="preview-section">
            <h4>Preview Dry-Run</h4>
            <div className="preview-info">
              <span>Decisão prevista: {preview.predictedDecision}</span>
              <span>Confiança: {Math.round(preview.confidence * 100)}%</span>
            </div>
          </div>
        )}

        {/* Rollback Alert */}
        {rollbackInfo && rollbackInfo.triggered && (
          <div className="rollback-alert">
            <h4>Rollback Acionado</h4>
            <p>{rollbackInfo.reason}</p>
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="loading-section" data-testid="loading-spinner">
            <span className="spinner">⟳</span>
            {status === 'executing' && <span>Executando...</span>}
          </div>
        )}
      </div>

      <div className="card-footer">
        <button
          onClick={simulate}
          disabled={isLoading}
          className="btn btn-secondary"
        >
          Preview
        </button>
        <button
          onClick={execute}
          disabled={isLoading || (safetyStatus && !safetyStatus.allowed)}
          className="btn btn-primary"
        >
          Executar com safety gates
        </button>
      </div>
    </div>
  );
};
