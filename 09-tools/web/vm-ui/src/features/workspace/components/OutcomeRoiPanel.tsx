/**
 * OutcomeRoiPanel Component (v36)
 * 
 * Studio panel for managing outcome attribution and hybrid ROI operations.
 */

import React, { useState } from 'react';
import { useOutcomeRoi, Proposal } from '../hooks/useOutcomeRoi';

interface OutcomeRoiPanelProps {
  brandId?: string;
}

const riskLevelColors: Record<string, string> = {
  low: 'bg-green-100 text-green-800 border-green-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  high: 'bg-red-100 text-red-800 border-red-200',
};

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-800 border-gray-200',
  applied: 'bg-green-100 text-green-800 border-green-200',
  rejected: 'bg-red-100 text-red-800 border-red-200',
  rolled_back: 'bg-orange-100 text-orange-800 border-orange-200',
};

const riskLevelLabels: Record<string, string> = {
  low: 'Baixo',
  medium: 'Médio',
  high: 'Alto',
};

const statusLabels: Record<string, string> = {
  pending: 'Pendente',
  applied: 'Aplicado',
  rejected: 'Rejeitado',
  rolled_back: 'Revertido',
};

function ProposalCard({ 
  proposal, 
  onApply,
  onReject,
}: { 
  proposal: Proposal; 
  onApply: (id: string) => void;
  onReject: (id: string) => void;
}) {
  const [isApplying, setIsApplying] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  const handleApply = async () => {
    setIsApplying(true);
    await onApply(proposal.proposal_id);
    setIsApplying(false);
  };

  const handleReject = async () => {
    setIsRejecting(true);
    await onReject(proposal.proposal_id);
    setIsRejecting(false);
  };

  return (
    <div className="border rounded-lg p-4 mb-3 bg-white shadow-sm">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h4 className="font-medium text-gray-900">{proposal.action}</h4>
          <p className="text-sm text-gray-500">
            {proposal.touchpoint_type}
          </p>
        </div>
        <div className="flex gap-2">
          <span className={`px-2 py-1 rounded text-xs font-medium border ${riskLevelColors[proposal.risk_level] || 'bg-gray-100'}`}>
            {riskLevelLabels[proposal.risk_level] || proposal.risk_level}
          </span>
          <span className={`px-2 py-1 rounded text-xs font-medium border ${statusColors[proposal.status] || 'bg-gray-100'}`}>
            {statusLabels[proposal.status] || proposal.status}
          </span>
        </div>
      </div>

      <div className="text-sm text-gray-600 mb-3">
        <p><span className="font-medium">Hybrid Index:</span> {proposal.hybrid_index.toFixed(3)}</p>
        <p><span className="font-medium">Criado:</span> {new Date(proposal.created_at).toLocaleDateString()}</p>
      </div>

      <div className="bg-gray-50 rounded p-2 mb-3 text-xs text-gray-600">
        <p className="font-medium mb-1">Explicação:</p>
        <p className="line-clamp-2">{proposal.score_explanation}</p>
      </div>

      {proposal.status === 'pending' && (
        <div className="flex gap-2">
          <button
            onClick={handleApply}
            disabled={isApplying || isRejecting}
            className="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
          >
            {isApplying ? 'Aplicando...' : 'Aplicar'}
          </button>
          <button
            onClick={handleReject}
            disabled={isApplying || isRejecting}
            className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50"
          >
            {isRejecting ? 'Rejeitando...' : 'Rejeitar'}
          </button>
        </div>
      )}
    </div>
  );
}

export function OutcomeRoiPanel({ brandId }: OutcomeRoiPanelProps) {
  const {
    status,
    proposals,
    metrics,
    loading,
    error,
    refresh,
    runAttribution,
    applyProposal,
    rejectProposal,
    freeze,
    rollback,
  } = useOutcomeRoi({ brandId, pollInterval: 30000 });

  const [isRunning, setIsRunning] = useState(false);
  const [isFreezing, setIsFreezing] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [freezeReason, setFreezeReason] = useState('');
  const [rollbackReason, setRollbackReason] = useState('');

  const handleRunAttribution = async () => {
    setIsRunning(true);
    await runAttribution({ outcome_type: 'activation', auto_apply_low_risk: true });
    setIsRunning(false);
  };

  const handleApply = async (proposalId: string) => {
    await applyProposal(proposalId);
  };

  const handleReject = async (proposalId: string) => {
    await rejectProposal(proposalId, 'Rejected by operator');
  };

  const handleFreeze = async () => {
    if (!freezeReason) return;
    setIsFreezing(true);
    await freeze(freezeReason);
    setIsFreezing(false);
    setFreezeReason('');
  };

  const handleRollback = async () => {
    if (!rollbackReason) return;
    setIsRollingBack(true);
    await rollback(rollbackReason);
    setIsRollingBack(false);
    setRollbackReason('');
  };

  const pendingProposals = proposals.filter(p => p.status === 'pending');
  const appliedProposals = proposals.filter(p => p.status === 'applied');
  const rejectedProposals = proposals.filter(p => p.status === 'rejected');

  const lowRiskCount = proposals.filter(p => p.risk_level === 'low').length;
  const mediumRiskCount = proposals.filter(p => p.risk_level === 'medium').length;
  const highRiskCount = proposals.filter(p => p.risk_level === 'high').length;

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            Outcome Attribution & Hybrid ROI
          </h2>
          <p className="text-gray-600 mt-1">
            v36: Attribution engine and hybrid ROI loop with quality guardrails
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleRunAttribution}
            disabled={isRunning || status?.frozen}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {isRunning ? 'Executando...' : 'Executar Atribuição'}
          </button>
          <button
            onClick={refresh}
            disabled={loading}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
          >
            {loading ? 'Atualizando...' : 'Atualizar'}
          </button>
        </div>
      </div>

      {status?.frozen && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-6">
          <p className="text-orange-800 font-medium">
            ⚠️ Operações congeladas
          </p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {metrics && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg border">
            <p className="text-sm text-gray-600">Outcomes Atribuídos</p>
            <p className="text-2xl font-bold text-gray-900">{metrics.outcomes_attributed}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border">
            <p className="text-sm text-gray-600">Proposals Geradas</p>
            <p className="text-2xl font-bold text-gray-900">{metrics.proposals_generated}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border">
            <p className="text-sm text-gray-600">Auto-Aplicadas</p>
            <p className="text-2xl font-bold text-green-600">{metrics.proposals_auto_applied}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border">
            <p className="text-sm text-gray-600">Aguardando Aprovação</p>
            <p className="text-2xl font-bold text-yellow-600">{metrics.proposals_pending_approval}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Proposals ({proposals.length})
          </h3>
          {proposals.length === 0 ? (
            <div className="bg-white p-8 rounded-lg border text-center text-gray-500">
              Nenhuma proposal gerada
            </div>
          ) : (
            <div>
              {proposals.map(proposal => (
                <ProposalCard
                  key={proposal.proposal_id}
                  proposal={proposal}
                  onApply={handleApply}
                  onReject={handleReject}
                />
              ))}
            </div>
          )}
        </div>

        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Resumo por Status
          </h3>
          <div className="bg-white p-4 rounded-lg border mb-4">
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600 font-medium">Pendentes</span>
                <span>{pendingProposals.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-green-600 font-medium">Aplicadas</span>
                <span>{appliedProposals.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-600 font-medium">Rejeitadas</span>
                <span>{rejectedProposals.length}</span>
              </div>
            </div>
          </div>

          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Distribuição de Risco
          </h3>
          <div className="bg-white p-4 rounded-lg border mb-4">
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-green-600 font-medium">Baixo</span>
                <span>{lowRiskCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-yellow-600 font-medium">Médio</span>
                <span>{mediumRiskCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-600 font-medium">Alto</span>
                <span>{highRiskCount}</span>
              </div>
            </div>
          </div>

          {metrics && (
            <>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Hybrid ROI
              </h3>
              <div className="bg-white p-4 rounded-lg border mb-4">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Index Médio</span>
                    <span className="font-medium">{metrics.hybrid_roi_index_avg.toFixed(3)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Payback (dias)</span>
                    <span className="font-medium">{metrics.payback_time_avg_days.toFixed(1)}</span>
                  </div>
                </div>
              </div>

              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Guardrails
              </h3>
              <div className="bg-white p-4 rounded-lg border mb-4">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Violações</span>
                    <span className="font-medium text-orange-600">{metrics.guardrail_violations}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Bloqueadas</span>
                    <span className="font-medium text-red-600">{metrics.proposals_blocked}</span>
                  </div>
                </div>
              </div>
            </>
          )}

          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Ações Supervisionadas
          </h3>
          <div className="space-y-3">
            <div className="bg-white p-4 rounded-lg border">
              <p className="text-sm font-medium text-gray-700 mb-2">Congelar Operações</p>
              <input
                type="text"
                placeholder="Motivo do congelamento"
                value={freezeReason}
                onChange={(e) => setFreezeReason(e.target.value)}
                className="w-full px-3 py-2 border rounded text-sm mb-2"
              />
              <button
                onClick={handleFreeze}
                disabled={isFreezing || !freezeReason || status?.frozen}
                className="w-full px-3 py-2 bg-orange-600 text-white text-sm rounded hover:bg-orange-700 disabled:opacity-50"
              >
                {isFreezing ? 'Congelando...' : 'Congelar'}
              </button>
            </div>

            <div className="bg-white p-4 rounded-lg border">
              <p className="text-sm font-medium text-gray-700 mb-2">Rollback</p>
              <input
                type="text"
                placeholder="Motivo do rollback"
                value={rollbackReason}
                onChange={(e) => setRollbackReason(e.target.value)}
                className="w-full px-3 py-2 border rounded text-sm mb-2"
              />
              <button
                onClick={handleRollback}
                disabled={isRollingBack || !rollbackReason}
                className="w-full px-3 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50"
              >
                {isRollingBack ? 'Revertendo...' : 'Executar Rollback'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default OutcomeRoiPanel;
