import React from 'react';
import { useRecoveryOrchestration, RecoveryRun, ApprovalRequest } from '../hooks/useRecoveryOrchestration';

interface RecoveryOrchestrationPanelProps {
  brandId: string;
}

export function RecoveryOrchestrationPanel({ brandId }: RecoveryOrchestrationPanelProps) {
  const {
    status,
    events,
    loading,
    error,
    processing,
    fetchStatus,
    startRecovery,
    approveRecovery,
    rejectRecovery,
    freezeRecovery,
    rollbackRecovery,
    retryRecovery,
    getSeverityColor,
    getStatusColor,
    canApprove,
    canReject,
    canFreeze,
    canRollback,
    canRetry,
  } = useRecoveryOrchestration();

  React.useEffect(() => {
    fetchStatus(brandId);
  }, [brandId, fetchStatus]);

  const handleStartRecovery = async () => {
    await startRecovery(brandId, 'handoff_timeout', 'medium', 'Manual recovery start');
  };

  const handleApprove = async (requestId: string) => {
    await approveRecovery(brandId, requestId, 'user-001', 'Approved via Studio');
  };

  const handleReject = async (requestId: string) => {
    await rejectRecovery(brandId, requestId, 'user-001', 'Rejected via Studio');
  };

  const handleFreeze = async (incidentId: string) => {
    await freezeRecovery(brandId, incidentId, 'Frozen via Studio');
  };

  const handleRollback = async (runId: string) => {
    await rollbackRecovery(brandId, runId, 'Rolled back via Studio');
  };

  const handleRetry = async (runId: string) => {
    await retryRecovery(brandId, runId);
  };

  if (loading) {
    return (
      <div data-testid="recovery-orchestration-loading" className="p-4 border rounded">
        <div className="flex items-center space-x-2">
          <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
          <span>Loading Recovery Orchestration...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div data-testid="recovery-orchestration-error" className="p-4 border rounded bg-red-50">
        <p className="text-red-600">{error}</p>
        <button
          onClick={() => fetchStatus(brandId)}
          className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Retry
        </button>
      </div>
    );
  }

  const pendingApprovals = status?.pending_approvals || [];
  const activeIncidents = status?.active_incidents || [];

  return (
    <div data-testid="recovery-orchestration-panel" className="p-4 border rounded bg-white">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h2 className="text-lg font-semibold">Recovery Orchestration v28</h2>
          <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded">
            {status?.version || 'v28'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <span
            data-testid="recovery-state"
            className={`px-2 py-0.5 text-xs rounded ${
              status?.state === 'frozen'
                ? 'bg-red-100 text-red-700'
                : status?.state === 'awaiting_approval'
                ? 'bg-yellow-100 text-yellow-700'
                : 'bg-green-100 text-green-700'
            }`}
          >
            {status?.state || 'idle'}
          </span>
          {processing && (
            <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
          )}
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-2 mb-4">
        <div data-testid="metric-total-runs" className="text-center p-2 bg-gray-50 rounded">
          <div className="text-lg font-semibold">{status?.metrics?.total_runs || 0}</div>
          <div className="text-xs text-gray-500">Total Runs</div>
        </div>
        <div data-testid="metric-successful" className="text-center p-2 bg-green-50 rounded">
          <div className="text-lg font-semibold text-green-600">{status?.metrics?.successful_runs || 0}</div>
          <div className="text-xs text-gray-500">Successful</div>
        </div>
        <div data-testid="metric-failed" className="text-center p-2 bg-red-50 rounded">
          <div className="text-lg font-semibold text-red-600">{status?.metrics?.failed_runs || 0}</div>
          <div className="text-xs text-gray-500">Failed</div>
        </div>
        <div data-testid="metric-pending-approvals" className="text-center p-2 bg-yellow-50 rounded">
          <div className="text-lg font-semibold text-yellow-600">{status?.metrics?.pending_approvals || 0}</div>
          <div className="text-xs text-gray-500">Pending</div>
        </div>
      </div>

      {/* Auto/Manual Split */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div data-testid="metric-auto-runs" className="text-center p-2 bg-blue-50 rounded">
          <div className="text-lg font-semibold text-blue-600">{status?.metrics?.auto_runs || 0}</div>
          <div className="text-xs text-gray-500">Auto-executed</div>
        </div>
        <div data-testid="metric-manual-runs" className="text-center p-2 bg-gray-50 rounded">
          <div className="text-lg font-semibold">{status?.metrics?.manual_runs || 0}</div>
          <div className="text-xs text-gray-500">Manual</div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex space-x-2 mb-4">
        <button
          data-testid="start-recovery-button"
          onClick={handleStartRecovery}
          disabled={processing}
          className="flex-1 px-3 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
        >
          Start Recovery
        </button>
      </div>

      {/* Pending Approvals */}
      {pendingApprovals.length > 0 && (
        <div data-testid="approvals-section" className="mb-4">
          <h3 className="text-sm font-medium mb-2">Pending Approvals ({pendingApprovals.length})</h3>
          <div className="space-y-2">
            {pendingApprovals.map((request) => (
              <ApprovalCard
                key={request.request_id}
                request={request}
                onApprove={() => handleApprove(request.request_id)}
                onReject={() => handleReject(request.request_id)}
                canApprove={canApprove(request)}
                canReject={canReject(request)}
                getSeverityColor={getSeverityColor}
              />
            ))}
          </div>
        </div>
      )}

      {/* Active Incidents */}
      {activeIncidents.length > 0 && (
        <div data-testid="incidents-section" className="mb-4">
          <h3 className="text-sm font-medium mb-2">Active Incidents ({activeIncidents.length})</h3>
          <div className="space-y-2">
            {activeIncidents.map((incident) => (
              <IncidentCard
                key={incident.incident_id}
                incident={incident}
                getSeverityColor={getSeverityColor}
              />
            ))}
          </div>
        </div>
      )}

      {/* Recent Events */}
      {events.length > 0 && (
        <div data-testid="events-section" className="mb-4">
          <h3 className="text-sm font-medium mb-2">Recent Events ({events.length})</h3>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {events.slice(0, 10).map((event) => (
              <EventCard key={event.event_id} event={event} />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {pendingApprovals.length === 0 && activeIncidents.length === 0 && events.length === 0 && (
        <div data-testid="empty-state" className="text-center py-8 text-gray-500">
          No active recoveries or pending approvals
        </div>
      )}
    </div>
  );
}

interface ApprovalCardProps {
  request: ApprovalRequest;
  onApprove: () => void;
  onReject: () => void;
  canApprove: boolean;
  canReject: boolean;
  getSeverityColor: (severity: string) => string;
}

function ApprovalCard({
  request,
  onApprove,
  onReject,
  canApprove,
  canReject,
  getSeverityColor,
}: ApprovalCardProps) {
  return (
    <div
      data-testid={`approval-card-${request.request_id}`}
      className="p-3 bg-yellow-50 rounded border border-yellow-200"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <span data-testid="approval-incident-type" className="text-sm font-medium">
            {request.incident_type}
          </span>
          <span
            data-testid="approval-severity"
            className={`text-xs px-1.5 py-0.5 rounded ${getSeverityColor(request.severity)} bg-white`}
          >
            {request.severity}
          </span>
        </div>
        <span
          data-testid="approval-status"
          className="text-xs px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700"
        >
          {request.status}
        </span>
      </div>

      <div className="text-xs text-gray-500 mb-2">
        Requested: {new Date(request.requested_at).toLocaleString()}
      </div>

      <div className="flex space-x-2">
        {canApprove && (
          <button
            data-testid="approve-button"
            onClick={onApprove}
            className="flex-1 px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600"
          >
            Approve
          </button>
        )}
        {canReject && (
          <button
            data-testid="reject-button"
            onClick={onReject}
            className="flex-1 px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
          >
            Reject
          </button>
        )}
      </div>
    </div>
  );
}

interface IncidentCardProps {
  incident: {
    incident_id: string;
    type: string;
    severity: string;
    description: string;
    timestamp: string;
  };
  getSeverityColor: (severity: string) => string;
}

function IncidentCard({ incident, getSeverityColor }: IncidentCardProps) {
  return (
    <div
      data-testid={`incident-card-${incident.incident_id}`}
      className="p-3 bg-gray-50 rounded border border-gray-200"
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center space-x-2">
          <span data-testid="incident-type" className="text-sm font-medium">
            {incident.type}
          </span>
          <span
            data-testid="incident-severity"
            className={`text-xs px-1.5 py-0.5 rounded ${getSeverityColor(incident.severity)} bg-white`}
          >
            {incident.severity}
          </span>
        </div>
      </div>
      <p data-testid="incident-description" className="text-xs text-gray-600">
        {incident.description}
      </p>
      <div className="text-xs text-gray-400 mt-1">
        {new Date(incident.timestamp).toLocaleString()}
      </div>
    </div>
  );
}

interface EventCardProps {
  event: {
    event_id: string;
    event_type: string;
    details: Record<string, unknown>;
    timestamp: string;
  };
}

function EventCard({ event }: EventCardProps) {
  const getEventIcon = (type: string): string => {
    const icons: Record<string, string> = {
      'recovery_auto_started': '🤖',
      'recovery_approval_requested': '⏳',
      'recovery_approved': '✅',
      'recovery_rejected': '❌',
      'recovery_frozen': '🧊',
      'recovery_rolled_back': '↩️',
    };
    return icons[type] || '📝';
  };

  return (
    <div
      data-testid={`event-card-${event.event_id}`}
      className="p-2 bg-white rounded border border-gray-100 text-xs"
    >
      <div className="flex items-center space-x-2">
        <span>{getEventIcon(event.event_type)}</span>
        <span data-testid="event-type" className="font-medium">
          {event.event_type}
        </span>
        <span className="text-gray-400 ml-auto">
          {new Date(event.timestamp).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}
