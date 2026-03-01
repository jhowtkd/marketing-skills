/**
 * Adaptive Escalation Panel (v21)
 * 
 * Panel for configuring and monitoring adaptive escalation.
 * Displays:
 * - Escalation window calculations
 * - Approver profiles
 * - Timeout rate metrics
 */

import React, { useEffect } from 'react';
import { useAdaptiveEscalation } from '../hooks/useAdaptiveEscalation';

export const AdaptiveEscalationPanel: React.FC = () => {
  const {
    windows,
    profile,
    metrics,
    isLoading,
    error,
    calculateWindows,
    loadProfile,
    loadMetrics,
  } = useAdaptiveEscalation();

  useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  const handleCalculate = () => {
    calculateWindows({
      stepId: 'step-demo',
      riskLevel: 'medium',
      approverId: 'admin@example.com',
      pendingCount: 5,
    });
  };

  const handleLoadProfile = () => {
    loadProfile('admin@example.com');
  };

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600 * 10) / 10}h`;
  };

  const getRiskColor = (riskLevel: string): string => {
    switch (riskLevel) {
      case 'low': return '#22c55e';
      case 'medium': return '#f59e0b';
      case 'high': return '#ef4444';
      case 'critical': return '#7f1d1d';
      default: return '#6b7280';
    }
  };

  return (
    <div className="adaptive-escalation-panel" data-testid="adaptive-escalation-panel">
      <header className="panel-header">
        <h2>Escalonamento Adaptativo v21</h2>
        <p className="panel-description">
          Reduz timeout em 30% e latência em 25% através de aprendizado histórico
        </p>
      </header>

      {/* Metrics Overview */}
      <section className="metrics-section" data-testid="escalation-metrics">
        <h3>Métricas</h3>
        {isLoading && !metrics && (
          <div className="loading" data-testid="metrics-loading">Carregando...</div>
        )}
        {metrics && (
          <div className="metrics-grid">
            <div className="metric-card" data-testid="metric-approver-count">
              <span className="metric-value">{metrics.approverCount}</span>
              <span className="metric-label">Aprovadores</span>
            </div>
            <div className="metric-card" data-testid="metric-total-approvals">
              <span className="metric-value">{metrics.totalApprovals}</span>
              <span className="metric-label">Aprovações</span>
            </div>
            <div className="metric-card" data-testid="metric-timeout-rate">
              <span className="metric-value">{(metrics.timeoutRate * 100).toFixed(1)}%</span>
              <span className="metric-label">Taxa Timeout</span>
            </div>
            <div className="metric-card" data-testid="metric-target-reduction">
              <span className="metric-value">-30%</span>
              <span className="metric-label">Meta Redução</span>
            </div>
          </div>
        )}
        {!isLoading && !metrics && !error && (
          <div className="empty-metrics">Nenhuma métrica disponível</div>
        )}
      </section>

      {/* Actions */}
      <section className="actions-section">
        <h3>Ações</h3>
        <div className="action-buttons">
          <button
            className="btn-calculate"
            data-testid="btn-calculate-windows"
            onClick={handleCalculate}
            disabled={isLoading}
          >
            Calcular Janelas
          </button>
          <button
            className="btn-profile"
            data-testid="btn-load-profile"
            onClick={handleLoadProfile}
            disabled={isLoading}
          >
            Ver Perfil
          </button>
          <button
            className="btn-refresh"
            data-testid="btn-refresh-metrics"
            onClick={loadMetrics}
            disabled={isLoading}
          >
            Atualizar Métricas
          </button>
        </div>
      </section>

      {/* Error Display */}
      {error && (
        <div className="error-banner" data-testid="escalation-error">
          {error}
        </div>
      )}

      {/* Escalation Windows */}
      {windows && (
        <section className="windows-section" data-testid="escalation-windows">
          <h3>Janelas de Escalonamento</h3>
          <div className="windows-display">
            {windows.windows.map((window, index) => (
              <div
                key={index}
                className={`window-level level-${index}`}
                data-testid={`window-level-${index}`}
              >
                <span className="level-number">Nível {index + 1}</span>
                <span className="level-timeout">{formatDuration(window)}</span>
              </div>
            ))}
          </div>
          <div className="adaptive-factors" data-testid="adaptive-factors">
            <h4>Fatores Adaptativos</h4>
            {windows.adaptiveFactors && (
              <>
                <div className="factor">
                  <span className="factor-label">Nível de Risco:</span>
                  <span
                    className="factor-value"
                    style={{ color: getRiskColor(windows.adaptiveFactors.riskLevel || 'medium') }}
                  >
                    {(windows.adaptiveFactors.riskLevel || 'MEDIUM').toUpperCase()}
                  </span>
                </div>
                <div className="factor">
                  <span className="factor-label">Carga Pendente:</span>
                  <span className="factor-value">{windows.adaptiveFactors.pendingLoad || 0}</span>
                </div>
              </>
            )}
          </div>
        </section>
      )}

      {/* Approver Profile */}
      {profile && (
        <section className="profile-section" data-testid="approver-profile">
          <h3>Perfil do Aprovador</h3>
          <div className="profile-card">
            <div className="profile-header">
              <span className="profile-id" data-testid="profile-id">
                {profile.approverId}
              </span>
              <span
                className={`timeout-rate ${profile.timeoutRate > 0.3 ? 'high' : 'low'}`}
                data-testid="profile-timeout-rate"
              >
                {(profile.timeoutRate * 100).toFixed(0)}% timeout
              </span>
            </div>
            <div className="profile-stats">
              <div className="stat">
                <span className="stat-value" data-testid="profile-avg-response">
                  {profile.avgResponseTimeMinutes.toFixed(1)}m
                </span>
                <span className="stat-label">Tempo Médio</span>
              </div>
              <div className="stat">
                <span className="stat-value" data-testid="profile-approvals">
                  {profile.approvalsCount}
                </span>
                <span className="stat-label">Aprovações</span>
              </div>
              <div className="stat">
                <span className="stat-value" data-testid="profile-timeouts">
                  {profile.timeoutsCount}
                </span>
                <span className="stat-label">Timeouts</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="loading-overlay" data-testid="escalation-loading">
          Processando...
        </div>
      )}
    </div>
  );
};

export default AdaptiveEscalationPanel;
