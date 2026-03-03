/**
 * OnboardingRecoveryPanel Component (v34)
 * 
 * Studio panel for managing onboarding recovery cases.
 */

import React, { useState } from 'react';
import { useOnboardingRecovery, RecoveryCase, RecoveryProposal } from '../hooks/useOnboardingRecovery';

interface OnboardingRecoveryPanelProps {
  brandId?: string;
}

const priorityColors: Record<string, string> = {
  high: 'bg-red-100 text-red-800 border-red-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-green-100 text-green-800 border-green-200',
};

const strategyLabels: Record<string, string> = {
  reminder: 'Lembrete',
  fast_lane: 'Caminho Rápido',
  template_boost: 'Templates Novos',
  guided_resume: 'Resumo Guiado',
};

function CaseCard({ 
  caseItem, 
  onApply, 
  onReject,
  pending 
}: { 
  caseItem: RecoveryCase; 
  onApply: (id: string) => void;
  onReject: (id: string) => void;
  pending?: RecoveryProposal;
}) {
  const [isApplying, setIsApplying] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  const handleApply = async () => {
    setIsApplying(true);
    await onApply(caseItem.case_id);
    setIsApplying(false);
  };

  const handleReject = async () => {
    setIsRejecting(true);
    await onReject(caseItem.case_id);
    setIsRejecting(false);
  };

  return (
    <div className="border rounded-lg p-4 mb-3 bg-white shadow-sm">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h4 className="font-medium text-gray-900">{caseItem.user_id}</h4>
          <p className="text-sm text-gray-500">
            Step {caseItem.current_step} of {caseItem.total_steps} ({Math.round(caseItem.progress_percentage)}%)
          </p>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium border ${priorityColors[caseItem.priority] || 'bg-gray-100'}`}>
          {caseItem.priority.toUpperCase()}
        </span>
      </div>

      <div className="text-sm text-gray-600 mb-3">
        <p><span className="font-medium">Razão:</span> {caseItem.reason}</p>
        <p><span className="font-medium">Dropoff:</span> {new Date(caseItem.dropoff_at).toLocaleDateString()}</p>
        {caseItem.expires_at && (
          <p><span className="font-medium">Expira:</span> {new Date(caseItem.expires_at).toLocaleDateString()}</p>
        )}
      </div>

      {pending && (
        <div className="bg-blue-50 rounded p-3 mb-3 text-sm">
          <p className="font-medium text-blue-900 mb-1">
            Estratégia: {strategyLabels[pending.strategy.strategy] || pending.strategy.strategy}
          </p>
          <p className="text-blue-700">{pending.strategy.reason}</p>
          <p className="text-blue-600 mt-1">
            Impacto esperado: {Math.round(pending.strategy.expected_impact * 100)}% | 
            Tempo: {pending.resume_path.estimated_completion_minutes}min
          </p>
          {pending.requires_approval && (
            <span className="inline-block mt-2 px-2 py-0.5 bg-orange-100 text-orange-800 text-xs rounded">
              Requer Aprovação
            </span>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleApply}
          disabled={isApplying || isRejecting}
          className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {isApplying ? 'Aplicando...' : pending?.requires_approval ? 'Solicitar Aprovação' : 'Aplicar'}
        </button>
        <button
          onClick={handleReject}
          disabled={isApplying || isRejecting}
          className="px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300 disabled:opacity-50"
        >
          {isRejecting ? 'Rejeitando...' : 'Rejeitar'}
        </button>
      </div>
    </div>
  );
}

export function OnboardingRecoveryPanel({ brandId }: OnboardingRecoveryPanelProps) {
  const {
    status,
    cases,
    pendingApprovals,
    metrics,
    loading,
    error,
    refresh,
    applyCase,
    rejectCase,
    freeze,
    rollback,
  } = useOnboardingRecovery({ brandId, pollInterval: 30000 });

  const [isFreezing, setIsFreezing] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleFreeze = async () => {
    setIsFreezing(true);
    setActionError(null);
    const success = await freeze('current-user', 'Emergency freeze from UI');
    if (!success) {
      setActionError('Failed to freeze recovery operations');
    }
    setIsFreezing(false);
  };

  const handleRollback = async () => {
    setIsRollingBack(true);
    setActionError(null);
    const success = await rollback('current-user', 'Rollback from UI');
    if (!success) {
      setActionError('Failed to rollback recovery actions');
    }
    setIsRollingBack(false);
  };

  const handleApply = async (caseId: string) => {
    setActionError(null);
    const success = await applyCase(caseId, 'current-user');
    if (!success) {
      setActionError(`Failed to apply case ${caseId}`);
    }
  };

  const handleReject = async (caseId: string) => {
    setActionError(null);
    const success = await rejectCase(caseId, 'current-user');
    if (!success) {
      setActionError(`Failed to reject case ${caseId}`);
    }
  };

  const getPendingForCase = (caseId: string): RecoveryProposal | undefined => {
    return pendingApprovals.find(p => p.case_id === caseId);
  };

  return (
    <div className="p-6 bg-gray-50 min-h-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Onboarding Recovery (v34)</h2>
          <p className="text-sm text-gray-500">
            Gerenciar casos de recuperação de usuários com dropoff
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={refresh}
            disabled={loading}
            className="px-3 py-1.5 bg-white border text-gray-700 text-sm rounded hover:bg-gray-50 disabled:opacity-50"
          >
            {loading ? 'Atualizando...' : 'Atualizar'}
          </button>
          <button
            onClick={handleFreeze}
            disabled={isFreezing || status?.frozen}
            className="px-3 py-1.5 bg-orange-100 text-orange-800 text-sm rounded hover:bg-orange-200 disabled:opacity-50"
          >
            {isFreezing ? 'Congelando...' : status?.frozen ? 'Congelado' : 'Congelar'}
          </button>
          <button
            onClick={handleRollback}
            disabled={isRollingBack}
            className="px-3 py-1.5 bg-red-100 text-red-800 text-sm rounded hover:bg-red-200 disabled:opacity-50"
          >
            {isRollingBack ? 'Revertendo...' : 'Rollback'}
          </button>
        </div>
      </div>

      {(error || actionError) && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error || actionError}
        </div>
      )}

      {metrics && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <p className="text-sm text-gray-500">Casos Detectados</p>
            <p className="text-2xl font-bold text-gray-900">{metrics.cases_total}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <p className="text-sm text-gray-500">Recuperáveis</p>
            <p className="text-2xl font-bold text-blue-600">{metrics.cases_recoverable}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <p className="text-sm text-gray-500">Recuperados</p>
            <p className="text-2xl font-bold text-green-600">{metrics.cases_recovered}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <p className="text-sm text-gray-500">Taxa de Sucesso</p>
            <p className="text-2xl font-bold text-purple-600">
              {metrics.cases_total > 0 
                ? Math.round((metrics.cases_recovered / metrics.cases_total) * 100) 
                : 0}%
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Casos Recuperáveis ({cases.length})
          </h3>
          {cases.length === 0 ? (
            <div className="bg-white p-8 rounded-lg border text-center text-gray-500">
              Nenhum caso recuperável no momento
            </div>
          ) : (
            <div>
              {cases.map(caseItem => (
                <CaseCard
                  key={caseItem.case_id}
                  caseItem={caseItem}
                  onApply={handleApply}
                  onReject={handleReject}
                  pending={getPendingForCase(caseItem.case_id)}
                />
              ))}
            </div>
          )}
        </div>

        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Pendentes de Aprovação ({pendingApprovals.length})
          </h3>
          {pendingApprovals.length === 0 ? (
            <div className="bg-white p-6 rounded-lg border text-center text-gray-500 text-sm">
              Nenhuma proposta pendente
            </div>
          ) : (
            <div className="space-y-2">
              {pendingApprovals.map(proposal => (
                <div key={proposal.case_id} className="bg-white p-3 rounded border text-sm">
                  <p className="font-medium">{proposal.user_id}</p>
                  <p className="text-gray-500">
                    {strategyLabels[proposal.strategy.strategy] || proposal.strategy.strategy}
                  </p>
                  <p className="text-gray-400 text-xs mt-1">
                    {new Date(proposal.created_at).toLocaleDateString()}
                  </p>
                </div>
              ))}
            </div>
          )}

          {metrics && (
            <div className="mt-6 bg-white p-4 rounded-lg border">
              <h4 className="font-medium text-gray-900 mb-3">Distribuição</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Alta Prioridade</span>
                  <span className="font-medium">{metrics.priority_high}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Média Prioridade</span>
                  <span className="font-medium">{metrics.priority_medium}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Baixa Prioridade</span>
                  <span className="font-medium">{metrics.priority_low}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default OnboardingRecoveryPanel;
