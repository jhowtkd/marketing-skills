import { useState, useCallback, useEffect } from 'react';

export type PolicyStatus = 'pending' | 'approved' | 'applied' | 'rejected' | 'blocked' | 'frozen';

export interface Policy {
  threshold: number;
  mode: string;
  source: 'global' | 'brand' | 'segment' | 'default';
  source_brand_id: string | null;
  source_segment: string | null;
  [key: string]: unknown;
}

export interface Proposal {
  proposal_id: string;
  brand_id: string;
  objective_key: string | null;
  current_value: number;
  proposed_value: number;
  adjustment_percent: number;
  status: PolicyStatus;
  created_at: string;
  approved_by?: string;
  approved_at?: string;
  applied_at?: string;
  rejection_reason?: string;
}

export interface UsePoliciesReturn {
  policy: Policy | null;
  proposals: Proposal[];
  isLoading: boolean;
  error: string | null;
  isFrozen: boolean;
  fetchPolicy: (brandId: string, segment?: string, objectiveKey?: string) => Promise<void>;
  fetchProposals: (brandId: string, status?: PolicyStatus) => Promise<void>;
  approveProposal: (brandId: string, proposalId: string, approver: string) => Promise<void>;
  rejectProposal: (brandId: string, proposalId: string, reason: string) => Promise<void>;
  freezePolicy: (brandId: string, reason: string) => Promise<void>;
  rollbackPolicy: (brandId: string, steps?: number) => Promise<void>;
}

const API_BASE = '/api/v2';

export function usePolicies(): UsePoliciesReturn {
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isFrozen, setIsFrozen] = useState(false);

  const fetchPolicy = useCallback(async (brandId: string, segment?: string, objectiveKey?: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (segment) params.append('segment', segment);
      if (objectiveKey) params.append('objective_key', objectiveKey);
      
      const url = `${API_BASE}/brands/${brandId}/policy/effective?${params.toString()}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch policy: ${response.statusText}`);
      }
      
      const data = await response.json();
      setPolicy(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchProposals = useCallback(async (brandId: string, status?: PolicyStatus) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      
      const url = `${API_BASE}/brands/${brandId}/policy/proposals?${params.toString()}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch proposals: ${response.statusText}`);
      }
      
      const data = await response.json();
      setProposals(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const approveProposal = useCallback(async (brandId: string, proposalId: string, approver: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const url = `${API_BASE}/brands/${brandId}/policy/proposals/${proposalId}/approve`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approver }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to approve proposal: ${response.statusText}`);
      }
      
      // Refresh proposals after approval
      await fetchProposals(brandId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [fetchProposals]);

  const rejectProposal = useCallback(async (brandId: string, proposalId: string, reason: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const url = `${API_BASE}/brands/${brandId}/policy/proposals/${proposalId}/reject`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to reject proposal: ${response.statusText}`);
      }
      
      // Refresh proposals after rejection
      await fetchProposals(brandId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [fetchProposals]);

  const freezePolicy = useCallback(async (brandId: string, reason: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const url = `${API_BASE}/brands/${brandId}/policy/freeze`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to freeze policy: ${response.statusText}`);
      }
      
      setIsFrozen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const rollbackPolicy = useCallback(async (brandId: string, steps: number = 1) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const url = `${API_BASE}/brands/${brandId}/policy/rollback`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to rollback policy: ${response.statusText}`);
      }
      
      // Refresh policy after rollback
      await fetchPolicy(brandId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, [fetchPolicy]);

  return {
    policy,
    proposals,
    isLoading,
    error,
    isFrozen,
    fetchPolicy,
    fetchProposals,
    approveProposal,
    rejectProposal,
    freezePolicy,
    rollbackPolicy,
  };
}
