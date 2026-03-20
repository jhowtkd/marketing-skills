/**
 * OnboardingContinuityPanel Component (v35)
 * 
 * Studio panel for managing cross-session onboarding continuity.
 */

import { useState } from 'react';
import { useOnboardingContinuity, HandoffBundle } from '../hooks/useOnboardingContinuity';

interface OnboardingContinuityPanelProps {
  brandId?: string;
}

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  in_progress: 'bg-blue-100 text-blue-800 border-blue-200',
  completed: 'bg-green-100 text-green-800 border-green-200',
  failed: 'bg-red-100 text-red-800 border-red-200',
};

const statusLabels: Record<string, string> = {
  pending: 'PENDENTE',
  in_progress: 'EM PROGRESSO',
  completed: 'COMPLETED',
  failed: 'FALHO',
};

const priorityLabels: Record<string, string> = {
  session: 'Sessão Ativa',
  recovery: 'Recuperação',
  default: 'Padrão',
};

function HandoffCard({ 
  handoff, 
  onResume 
}: { 
  handoff: HandoffBundle; 
  onResume: (id: string) => void;
}) {
  const [isResuming, setIsResuming] = useState(false);

  const handleResume = async () => {
    setIsResuming(true);
    await onResume(handoff.bundle_id);
    setIsResuming(false);
  };

  const context = handoff.context_payload;
  const stepNumber = context?.current_step_number || 0;
  const completedCount = context?.completed_steps?.length || 0;

  return (
    <div className="border rounded-lg p-4 mb-3 bg-white shadow-sm">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h4 className="font-medium text-gray-900">{handoff.user_id}</h4>
          <p className="text-sm text-gray-500">
            Step {stepNumber} | {completedCount} completados
          </p>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium border ${statusColors[handoff.status] || 'bg-gray-100'}`}>
          {statusLabels[handoff.status] || handoff.status.toUpperCase()}
        </span>
      </div>

      <div className="text-sm text-gray-600 mb-3">
        <p><span className="font-medium">Fonte:</span> {priorityLabels[handoff.source_priority] || handoff.source_priority}</p>
        <p><span className="font-medium">Sessão Origem:</span> {handoff.source_session}</p>
        {handoff.target_session && (
          <p><span className="font-medium">Sessão Destino:</span> {handoff.target_session}</p>
        )}
        <p><span className="font-medium">Criado:</span> {new Date(handoff.created_at).toLocaleDateString()}</p>
      </div>

      {handoff.failure_reason && (
        <div className="bg-red-50 rounded p-2 mb-3 text-sm text-red-700">
          <span className="font-medium">Falha:</span> {handoff.failure_reason}
        </div>
      )}

      {handoff.status === 'pending' && (
        <button
          onClick={handleResume}
          disabled={isResuming}
          className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {isResuming ? 'Retomando...' : 'Retomar'}
        </button>
      )}
    </div>
  );
}

export function OnboardingContinuityPanel({ brandId }: OnboardingContinuityPanelProps) {
  const {
    status,
    handoffs,
    metrics,
    loading,
    error,
    refresh,
    resumeHandoff,
    freeze,
    rollback,
  } = useOnboardingContinuity({ brandId, pollInterval: 30000 });

  const [isFreezing, setIsFreezing] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleFreeze = async () => {
    setIsFreezing(true);
    setActionError(null);
    const success = await freeze('current-user', 'Emergency freeze from UI');
    if (!success) {
      setActionError('Failed to freeze continuity operations');
    }
    setIsFreezing(false);
  };

  const handleRollback = async () => {
    setIsRollingBack(true);
    setActionError(null);
    const success = await rollback('current-user', 'Rollback from UI');
    if (!success) {
      setActionError('Failed to rollback continuity operations');
    }
    setIsRollingBack(false);
  };

  const handleResume = async (bundleId: string) => {
    setActionError(null);
    const result = await resumeHandoff(bundleId, `session-${Date.now()}`, 'current-user');
    if (!result) {
      setActionError(`Failed to resume handoff ${bundleId}`);
    } else if (result.needsApproval) {
      setActionError(`Handoff ${bundleId} requires approval due to conflicts`);
    }
  };

  const pendingCount = handoffs.filter(h => h.status === 'pending').length;
  const completedCount = handoffs.filter(h => h.status === 'completed').length;
  const failedCount = handoffs.filter(h => h.status === 'failed').length;

  return (
    <div className="p-6 bg-gray-50 min-h-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Onboarding Continuity (v35)</h2>
          <p className="text-sm text-gray-500">
            Gerenciar continuidade cross-session entre checkpoints
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
            <p className="text-sm text-gray-500">Checkpoints Criados</p>
            <p className="text-2xl font-bold text-gray-900">{metrics.checkpoints_created}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <p className="text-sm text-gray-500">Handoffs Completados</p>
            <p className="text-2xl font-bold text-green-600">{metrics.bundles_completed}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <p className="text-sm text-gray-500">Pendentes</p>
            <p className="text-2xl font-bold text-yellow-600">{metrics.bundles_pending}</p>
          </div>
          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <p className="text-sm text-gray-500">Taxa de Sucesso</p>
            <p className="text-2xl font-bold text-blue-600">
              {metrics.bundles_created > 0 
                ? Math.round((metrics.bundles_completed / metrics.bundles_created) * 100) 
                : 0}%
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Handoffs Recentes ({handoffs.length})
          </h3>
          {handoffs.length === 0 ? (
            <div className="bg-white p-8 rounded-lg border text-center text-gray-500">
              Nenhum handoff recente
            </div>
          ) : (
            <div>
              {handoffs.map(handoff => (
                <HandoffCard
                  key={handoff.bundle_id}
                  handoff={handoff}
                  onResume={handleResume}
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
                <span className="text-yellow-600 font-medium">Pendentes</span>
                <span>{pendingCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-600 font-medium">Em Progresso</span>
                <span>{handoffs.filter(h => h.status === 'in_progress').length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-green-600 font-medium">Completados</span>
                <span>{completedCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-600 font-medium">Falhos</span>
                <span>{failedCount}</span>
              </div>
            </div>
          </div>

          {metrics && (
            <>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Fonte de Dados
              </h3>
              <div className="bg-white p-4 rounded-lg border mb-4">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Sessão</span>
                    <span className="font-medium">{metrics.source_session_count || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Recuperação</span>
                    <span className="font-medium">{metrics.source_recovery_count || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Padrão</span>
                    <span className="font-medium">{metrics.source_default_count || 0}</span>
                  </div>
                </div>
              </div>

              <h3 className="text-lg font-semibold text-gray-900 mb-3">
                Conflitos & Perdas
              </h3>
              <div className="bg-white p-4 rounded-lg border">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Conflitos Detectados</span>
                    <span className="font-medium text-orange-600">{metrics.conflicts_detected || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Perdas de Contexto</span>
                    <span className="font-medium text-red-600">{metrics.context_loss_events || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Necessitam Aprovação</span>
                    <span className="font-medium">{metrics.resumes_needing_approval || 0}</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default OnboardingContinuityPanel;
