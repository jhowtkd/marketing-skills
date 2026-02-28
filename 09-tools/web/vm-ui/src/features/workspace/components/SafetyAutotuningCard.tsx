/**
 * SafetyAutotuningCard.tsx
 * 
 * Card "Safety Auto-Tuning" para o Control Center.
 * 
 * Features:
 * - Status dos gates de segurança
 * - Lista de propostas de ajuste
 * - Botões Apply/Revert/Freeze
 * - Indicadores de risco
 */

import React, { useState } from 'react';
import { useSafetyAutotuning } from '../hooks/useSafetyAutotuning';

export const SafetyAutotuningCard: React.FC = () => {
  const {
    status,
    lastCycleAt,
    gates,
    frozenGates,
    activeCanaries,
    currentCycle,
    runCycle,
    applyProposal,
    revertProposal,
    freezeGate,
    unfreezeGate,
    refreshStatus,
  } = useSafetyAutotuning();

  const [isRunning, setIsRunning] = useState(false);
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [revertingId, setRevertingId] = useState<string | null>(null);
  const [freezingGate, setFreezingGate] = useState<string | null>(null);

  const handleRunCycle = async () => {
    setIsRunning(true);
    await runCycle('propose');
    setIsRunning(false);
  };

  const handleApply = async (proposalId: string) => {
    setApplyingId(proposalId);
    await applyProposal(proposalId, false);
    setApplyingId(null);
    await refreshStatus();
  };

  const handleRevert = async (proposalId: string) => {
    setRevertingId(proposalId);
    await revertProposal(proposalId);
    setRevertingId(null);
    await refreshStatus();
  };

  const handleFreeze = async (gateName: string) => {
    setFreezingGate(gateName);
    await freezeGate(gateName);
    setFreezingGate(null);
  };

  const handleUnfreeze = async (gateName: string) => {
    setFreezingGate(gateName);
    await unfreezeGate(gateName);
    setFreezingGate(null);
  };

  const getRiskBadgeClass = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low':
        return 'badge-low';
      case 'medium':
        return 'badge-medium';
      case 'high':
        return 'badge-high';
      case 'critical':
        return 'badge-critical';
      default:
        return '';
    }
  };

  const getRiskLabel = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low':
        return 'Baixo';
      case 'medium':
        return 'Médio';
      case 'high':
        return 'Alto';
      case 'critical':
        return 'Crítico';
      default:
        return riskLevel;
    }
  };

  const formatAdjustment = (percent: number) => {
    const sign = percent >= 0 ? '+' : '';
    return `${sign}${percent.toFixed(1)}%`;
  };

  return (
    <div className="safety-autotuning-card" data-testid="safety-autotuning-card">
      <div className="card-header">
        <h3>Safety Auto-Tuning</h3>
        <span className="status-badge" data-testid="tuning-status">
          {status === 'loading' ? 'Carregando...' : 'Ativo'}
        </span>
        {lastCycleAt && (
          <span className="last-cycle">
            Último ciclo: {new Date(lastCycleAt).toLocaleString()}
          </span>
        )}
      </div>

      <div className="card-body">
        {/* Gates Status */}
        <div className="gates-section" data-testid="gates-status">
          <h4>Status dos Gates</h4>
          {gates.length === 0 ? (
            <div className="empty-state">Nenhum gate configurado</div>
          ) : (
            <div className="gates-list">
              {gates.map((gate) => (
                <div
                  key={gate.name}
                  className={`gate-item ${gate.isFrozen ? 'frozen' : ''}`}
                  data-testid={`gate-${gate.name}`}
                >
                  <div className="gate-info">
                    <span className="gate-name">{gate.name}</span>
                    <span className="gate-value">
                      {gate.currentValue}
                      {gate.isCanaryActive && (
                        <span className="canary-indicator" title="Canary ativo">
                          🧪
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="gate-actions">
                    {gate.isFrozen ? (
                      <button
                        className="btn-unfreeze"
                        onClick={() => handleUnfreeze(gate.name)}
                        disabled={freezingGate === gate.name}
                        data-testid={`unfreeze-${gate.name}`}
                      >
                        {freezingGate === gate.name ? '...' : 'Descongelar'}
                      </button>
                    ) : (
                      <button
                        className="btn-freeze"
                        onClick={() => handleFreeze(gate.name)}
                        disabled={freezingGate === gate.name}
                        data-testid={`freeze-${gate.name}`}
                      >
                        {freezingGate === gate.name ? '...' : 'Congelar'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Proposals */}
        <div className="proposals-section" data-testid="proposals-section">
          <h4>Propostas de Ajuste</h4>
          {!currentCycle ? (
            <div className="empty-state">
              Nenhum ciclo executado. Clique em "Analisar" para gerar propostas.
            </div>
          ) : currentCycle.proposals.length === 0 ? (
            <div className="empty-state">Nenhuma proposta gerada</div>
          ) : (
            <div className="proposals-list">
              {currentCycle.proposals.map((proposal) => (
                <div
                  key={proposal.proposalId}
                  className={`proposal-item ${proposal.blockedByVolume ? 'blocked' : ''}`}
                  data-testid={`proposal-${proposal.proposalId}`}
                >
                  <div className="proposal-header">
                    <span className="proposal-gate">{proposal.gateName}</span>
                    <span className={`risk-badge ${getRiskBadgeClass(proposal.riskLevel)}`}>
                      {getRiskLabel(proposal.riskLevel)}
                    </span>
                  </div>

                  <div className="proposal-details">
                    <div className="value-change">
                      <span className="old-value">{proposal.currentValue}</span>
                      <span className="arrow">→</span>
                      <span className="new-value">{proposal.proposedValue}</span>
                      <span
                        className={`adjustment ${
                          proposal.adjustmentPercent >= 0 ? 'positive' : 'negative'
                        }`}
                      >
                        {formatAdjustment(proposal.adjustmentPercent)}
                      </span>
                    </div>
                    <div className="proposal-reason">{proposal.reason}</div>
                  </div>

                  {!proposal.blockedByVolume && (
                    <div className="proposal-actions">
                      <button
                        className="btn-apply"
                        onClick={() => handleApply(proposal.proposalId)}
                        disabled={applyingId === proposal.proposalId}
                        data-testid={`apply-${proposal.proposalId}`}
                      >
                        {applyingId === proposal.proposalId ? 'Aplicando...' : 'Aplicar'}
                      </button>
                      <button
                        className="btn-revert"
                        onClick={() => handleRevert(proposal.proposalId)}
                        disabled={revertingId === proposal.proposalId}
                        data-testid={`revert-${proposal.proposalId}`}
                      >
                        {revertingId === proposal.proposalId ? 'Revertendo...' : 'Reverter'}
                      </button>
                    </div>
                  )}

                  {proposal.blockedByVolume && (
                    <div className="blocked-notice">
                      Bloqueado: volume insuficiente
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card-footer">
        <button
          className="btn-primary"
          onClick={handleRunCycle}
          disabled={isRunning || status === 'loading'}
          data-testid="run-cycle-btn"
        >
          {isRunning ? 'Analisando...' : 'Analisar'}
        </button>
        <button
          className="btn-secondary"
          onClick={refreshStatus}
          disabled={status === 'loading'}
          data-testid="refresh-btn"
        >
          Atualizar
        </button>
      </div>
    </div>
  );
};
