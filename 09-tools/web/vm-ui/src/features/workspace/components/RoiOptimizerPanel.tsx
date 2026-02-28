/**
 * ROI Optimizer Panel (v19)
 *
 * Displays ROI composite score, pillar contributions, and optimization proposals.
 * Supports apply/reject/rollback actions with pillar transparency.
 */

import React from 'react';
import { useRoiOptimizer, RoiProposal } from '../hooks/useRoiOptimizer';

interface ScoreCardProps {
  title: string;
  score: number;
  weight?: number;
  color: string;
}

const ScoreCard: React.FC<ScoreCardProps> = ({ title, score, weight, color }) => (
  <div className="score-card" data-testid={`score-card-${title.toLowerCase().replace(/\s+/g, '-')}`}>
    <div className="score-header" style={{ borderLeftColor: color }}>
      <span className="score-title">{title}</span>
      {weight !== undefined && (
        <span className="score-weight" data-testid={`${title.toLowerCase()}-weight`}>
          {Math.round(weight * 100)}%
        </span>
      )}
    </div>
    <div className="score-value" data-testid={`${title.toLowerCase().replace(/\s+/g, '-')}-value`}>
      {(score * 100).toFixed(1)}%
    </div>
  </div>
);

interface ProposalCardProps {
  proposal: RoiProposal;
  onApply: (id: string) => void;
  onReject: (id: string) => void;
}

const ProposalCard: React.FC<ProposalCardProps> = ({ proposal, onApply, onReject }) => {
  const riskColors: Record<string, string> = {
    low: '#22c55e',
    medium: '#f59e0b',
    high: '#ef4444',
    critical: '#7f1d1d',
  };

  const statusLabels: Record<string, string> = {
    pending: 'Pendente',
    approved: 'Aprovado',
    rejected: 'Rejeitado',
    blocked: 'Bloqueado',
    applied: 'Aplicado',
  };

  return (
    <div 
      className={`proposal-card proposal-status-${proposal.status}`}
      data-testid={`proposal-${proposal.id}`}
    >
      <div className="proposal-header">
        <span className="proposal-id">{proposal.id}</span>
        <span 
          className={`proposal-risk risk-${proposal.risk_level}`}
          data-testid={`proposal-risk-${proposal.id}`}
          style={{ color: riskColors[proposal.risk_level] }}
        >
          {proposal.risk_level.toUpperCase()}
        </span>
        <span 
          className={`proposal-status status-${proposal.status}`}
          data-testid={`proposal-status-${proposal.id}`}
        >
          {statusLabels[proposal.status]}
        </span>
      </div>
      
      <p className="proposal-description" data-testid={`proposal-desc-${proposal.id}`}>
        {proposal.description}
      </p>
      
      <div className="proposal-metrics">
        <span className="proposal-delta" data-testid={`proposal-delta-${proposal.id}`}>
          Δ ROI: +{(proposal.expected_roi_delta * 100).toFixed(1)}%
        </span>
        {proposal.autoapply_eligible && (
          <span className="autoapply-badge" data-testid={`proposal-autoapply-${proposal.id}`}>
            Auto-aplicável
          </span>
        )}
      </div>

      {proposal.block_reason && (
        <div className="block-reason" data-testid={`proposal-block-reason-${proposal.id}`}>
          ⚠️ {proposal.block_reason}
        </div>
      )}

      {proposal.status === 'pending' && (
        <div className="proposal-actions">
          <button
            className="btn-apply"
            data-testid={`btn-apply-${proposal.id}`}
            onClick={() => onApply(proposal.id)}
            disabled={proposal.status !== 'pending'}
          >
            Aplicar
          </button>
          <button
            className="btn-reject"
            data-testid={`btn-reject-${proposal.id}`}
            onClick={() => onReject(proposal.id)}
            disabled={proposal.status !== 'pending'}
          >
            Rejeitar
          </button>
        </div>
      )}
    </div>
  );
};

export const RoiOptimizerPanel: React.FC = () => {
  const {
    status,
    proposals,
    isLoading,
    error,
    runOptimization,
    applyProposal,
    rejectProposal,
    rollback,
    hasPendingProposals,
    hasAutoapplyEligibleProposals,
    getProposalsByStatus,
  } = useRoiOptimizer();

  const handleRunOptimization = () => {
    runOptimization({
      approval_without_regen_24h: 0.70,
      revenue_attribution_usd: 100000,
      regen_per_job: 0.5,
      quality_score_avg: 0.80,
      avg_latency_ms: 150,
      cost_per_job_usd: 0.05,
      incident_rate: 0.01,
    });
  };

  const pendingProposals = getProposalsByStatus('pending');
  const appliedProposals = getProposalsByStatus('applied');
  const blockedProposals = getProposalsByStatus('blocked');

  // Loading state
  if (isLoading && !status) {
    return (
      <div className="roi-optimizer-panel loading" data-testid="roi-panel-loading">
        <div className="loading-spinner">Carregando...</div>
      </div>
    );
  }

  // Error state
  if (error && !status) {
    return (
      <div className="roi-optimizer-panel error" data-testid="roi-panel-error">
        <div className="error-message">
          <h3>Erro</h3>
          <p>{error}</p>
          <button onClick={handleRunOptimization}>Tentar novamente</button>
        </div>
      </div>
    );
  }

  // Empty state (no data yet)
  if (!status) {
    return (
      <div className="roi-optimizer-panel empty" data-testid="roi-panel-empty">
        <div className="empty-state">
          <h3>Otimizador de ROI</h3>
          <p>Nenhuma otimização executada ainda.</p>
          <button 
            className="btn-run"
            data-testid="btn-run-empty"
            onClick={handleRunOptimization}
          >
            Executar Otimização
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="roi-optimizer-panel" data-testid="roi-optimizer-panel">
      <header className="panel-header">
        <h2>Otimizador de ROI v19</h2>
        <div className="panel-meta">
          <span className="mode-badge" data-testid="roi-mode">
            {status.mode}
          </span>
          <span className="cadence-badge" data-testid="roi-cadence">
            {status.cadence}
          </span>
        </div>
      </header>

      {/* Composite Score Section */}
      {status.current_score && (
        <section className="scores-section" data-testid="roi-scores">
          <h3>Score Composto</h3>
          <div className="scores-grid">
            <ScoreCard
              title="Total"
              score={status.current_score.total}
              color="#3b82f6"
            />
            <ScoreCard
              title="Business"
              score={status.current_score.business}
              weight={status.weights.business}
              color="#22c55e"
            />
            <ScoreCard
              title="Quality"
              score={status.current_score.quality}
              weight={status.weights.quality}
              color="#f59e0b"
            />
            <ScoreCard
              title="Efficiency"
              score={status.current_score.efficiency}
              weight={status.weights.efficiency}
              color="#8b5cf6"
            />
          </div>
        </section>
      )}

      {/* Actions */}
      <section className="actions-section" data-testid="roi-actions">
        <button
          className="btn-run"
          data-testid="btn-run-optimization"
          onClick={handleRunOptimization}
          disabled={isLoading}
        >
          {isLoading ? 'Executando...' : 'Executar Otimização'}
        </button>
        
        {appliedProposals.length > 0 && (
          <button
            className="btn-rollback"
            data-testid="btn-rollback"
            onClick={rollback}
            disabled={isLoading}
          >
            Rollback ({appliedProposals.length})
          </button>
        )}

        {hasAutoapplyEligibleProposals && (
          <span className="autoapply-hint" data-testid="autoapply-hint">
            ⚡ Propostas elegíveis para auto-aplicação
          </span>
        )}
      </section>

      {/* Error display */}
      {error && (
        <div className="error-banner" data-testid="roi-error-banner">
          {error}
        </div>
      )}

      {/* Proposals Section */}
      <section className="proposals-section" data-testid="roi-proposals">
        <h3>Propostas ({proposals.length})</h3>
        
        {proposals.length === 0 ? (
          <div className="no-proposals" data-testid="no-proposals">
            Nenhuma proposta gerada. Execute a otimização.
          </div>
        ) : (
          <div className="proposals-list">
            {/* Pending proposals first */}
            {pendingProposals.length > 0 && (
              <div className="proposals-group" data-testid="pending-proposals">
                <h4>Pendentes ({pendingProposals.length})</h4>
                {pendingProposals.map(proposal => (
                  <ProposalCard
                    key={proposal.id}
                    proposal={proposal}
                    onApply={applyProposal}
                    onReject={rejectProposal}
                  />
                ))}
              </div>
            )}

            {/* Blocked proposals */}
            {blockedProposals.length > 0 && (
              <div className="proposals-group blocked" data-testid="blocked-proposals">
                <h4>Bloqueadas ({blockedProposals.length})</h4>
                {blockedProposals.map(proposal => (
                  <ProposalCard
                    key={proposal.id}
                    proposal={proposal}
                    onApply={applyProposal}
                    onReject={rejectProposal}
                  />
                ))}
              </div>
            )}

            {/* Applied proposals */}
            {appliedProposals.length > 0 && (
              <div className="proposals-group applied" data-testid="applied-proposals">
                <h4>Aplicadas ({appliedProposals.length})</h4>
                {appliedProposals.map(proposal => (
                  <ProposalCard
                    key={proposal.id}
                    proposal={proposal}
                    onApply={applyProposal}
                    onReject={rejectProposal}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Last run info */}
      {status.last_run_at && (
        <footer className="panel-footer" data-testid="roi-footer">
          Última execução: {new Date(status.last_run_at).toLocaleString('pt-BR')}
        </footer>
      )}
    </div>
  );
};

export default RoiOptimizerPanel;
