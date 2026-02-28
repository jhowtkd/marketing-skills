import type { Policy, Proposal, PolicyStatus } from '../hooks/usePolicies';

interface PoliciesPanelProps {
  policy: Policy | null;
  proposals: Proposal[];
  isLoading: boolean;
  error: string | null;
  onApprove: (proposalId: string) => void;
  onReject: (proposalId: string) => void;
  onFreeze: () => void;
  onRollback: () => void;
  isFrozen: boolean;
}

function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value}%`;
}

function getStatusColor(status: PolicyStatus): string {
  switch (status) {
    case 'pending':
      return 'text-yellow-600 bg-yellow-50';
    case 'approved':
      return 'text-blue-600 bg-blue-50';
    case 'applied':
      return 'text-green-600 bg-green-50';
    case 'rejected':
      return 'text-red-600 bg-red-50';
    case 'blocked':
      return 'text-orange-600 bg-orange-50';
    case 'frozen':
      return 'text-gray-600 bg-gray-50';
    default:
      return 'text-gray-600 bg-gray-50';
  }
}

export function PoliciesPanel({
  policy,
  proposals,
  isLoading,
  error,
  onApprove,
  onReject,
  onFreeze,
  onRollback,
  isFrozen,
}: PoliciesPanelProps) {
  if (isLoading) {
    return (
      <div className="p-4">
        <div className="flex items-center justify-center h-32">
          <div className="text-gray-500">Loading policies...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4" role="alert">
          <div className="flex items-center gap-2 text-red-700">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="font-medium">Error loading policies</span>
          </div>
          <p className="mt-1 text-sm text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  const pendingProposals = proposals.filter(p => p.status === 'pending');
  const otherProposals = proposals.filter(p => p.status !== 'pending');

  return (
    <div className="p-4 space-y-6">
      {/* Frozen Banner */}
      {isFrozen && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-center gap-2 text-blue-700">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <span className="font-medium">Policy is frozen</span>
          </div>
          <p className="mt-1 text-sm text-blue-600">
            New proposals are temporarily disabled.
          </p>
        </div>
      )}

      {/* Effective Policy */}
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Effective Policy</h3>
        {policy ? (
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-500">Threshold</div>
                <div className="text-lg font-medium text-gray-900">{policy.threshold}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500">Mode</div>
                <div className="text-lg font-medium text-gray-900">{policy.mode}</div>
              </div>
            </div>
            <div className="pt-3 border-t border-gray-200">
              <div className="text-sm text-gray-500">Source</div>
              <div className="flex items-center gap-2 mt-1">
                <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                  policy.source === 'global' ? 'bg-gray-100 text-gray-700' :
                  policy.source === 'brand' ? 'bg-blue-100 text-blue-700' :
                  policy.source === 'segment' ? 'bg-purple-100 text-purple-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {policy.source}
                </span>
                {policy.source_brand_id && (
                  <span className="text-sm text-gray-600">{policy.source_brand_id}</span>
                )}
                {policy.source_segment && (
                  <span className="text-sm text-gray-600">({policy.source_segment})</span>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-gray-500 text-sm">No effective policy configured</div>
        )}
      </section>

      {/* Control Actions */}
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">Controls</h3>
        <div className="flex gap-2">
          <button
            onClick={onFreeze}
            disabled={isLoading || isFrozen}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Freeze
          </button>
          <button
            onClick={onRollback}
            disabled={isLoading}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
            </svg>
            Rollback
          </button>
        </div>
      </section>

      {/* Pending Proposals */}
      <section>
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          Pending Proposals
          {pendingProposals.length > 0 && (
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({pendingProposals.length})
            </span>
          )}
        </h3>
        
        {pendingProposals.length === 0 ? (
          <div className="text-gray-500 text-sm py-4">No pending proposals</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-700">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Objective</th>
                  <th className="px-3 py-2 text-left font-medium">Change</th>
                  <th className="px-3 py-2 text-left font-medium">Status</th>
                  <th className="px-3 py-2 text-left font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {pendingProposals.map((proposal) => (
                  <tr key={proposal.proposal_id} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <div className="font-medium text-gray-900">
                        {proposal.objective_key || 'global'}
                      </div>
                      <div className="text-xs text-gray-500">
                        {proposal.current_value} → {proposal.proposed_value}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <span className={`font-medium ${
                        proposal.adjustment_percent >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatPercent(proposal.adjustment_percent)}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getStatusColor(proposal.status)}`}>
                        {proposal.status}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <button
                          onClick={() => onApprove(proposal.proposal_id)}
                          disabled={isLoading}
                          className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:opacity-50"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => onReject(proposal.proposal_id)}
                          disabled={isLoading}
                          className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Other Proposals */}
      {otherProposals.length > 0 && (
        <section>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">
            Previous Proposals
            <span className="ml-2 text-sm font-normal text-gray-500">
              ({otherProposals.length})
            </span>
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-700">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Objective</th>
                  <th className="px-3 py-2 text-left font-medium">Change</th>
                  <th className="px-3 py-2 text-left font-medium">Status</th>
                  <th className="px-3 py-2 text-left font-medium">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {otherProposals.map((proposal) => (
                  <tr key={proposal.proposal_id} className="hover:bg-gray-50">
                    <td className="px-3 py-2">
                      <div className="font-medium text-gray-900">
                        {proposal.objective_key || 'global'}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <span className={`font-medium ${
                        proposal.adjustment_percent >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatPercent(proposal.adjustment_percent)}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getStatusColor(proposal.status)}`}>
                        {proposal.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500">
                      {proposal.approved_by && `Approved by ${proposal.approved_by}`}
                      {proposal.rejection_reason && `Rejected: ${proposal.rejection_reason}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
