/**
 * useSafetyAutotuning.ts
 * 
 * Hook para gerenciar o estado do Safety Auto-Tuning.
 * 
 * Features:
 * - Fetch status dos gates
 * - Executar ciclo de proposta
 * - Aplicar/reverter ajustes
 * - Congelar/descongelar gates
 */

import { useState, useCallback, useEffect } from 'react';

export interface GateStatus {
  name: string;
  currentValue: number;
  minValue: number;
  maxValue: number;
  isFrozen: boolean;
  isCanaryActive: boolean;
}

export interface TuningProposal {
  proposalId: string;
  gateName: string;
  currentValue: number;
  proposedValue: number;
  adjustmentPercent: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  reason: string;
  blockedByVolume?: boolean;
}

export interface TuningCycle {
  cycleId: string;
  proposals: TuningProposal[];
  proposalsCount: number;
  timestamp: string;
}

export interface AuditEntry {
  type: string;
  cycleId?: string;
  proposalId?: string;
  timestamp: string;
  [key: string]: any;
}

interface UseSafetyAutotuningReturn {
  // Status
  status: 'idle' | 'loading' | 'error';
  lastCycleAt: string | null;
  gates: GateStatus[];
  frozenGates: string[];
  activeCanaries: string[];
  
  // Ciclo atual
  currentCycle: TuningCycle | null;
  
  // Auditoria
  audit: AuditEntry[];
  
  // Ações
  refreshStatus: () => Promise<void>;
  runCycle: (mode?: 'propose' | 'dry-run') => Promise<TuningCycle | null>;
  applyProposal: (proposalId: string, auto?: boolean) => Promise<boolean>;
  revertProposal: (proposalId: string) => Promise<boolean>;
  freezeGate: (gateName: string, reason?: string) => Promise<boolean>;
  unfreezeGate: (gateName: string) => Promise<boolean>;
  refreshAudit: () => Promise<void>;
}

const API_BASE = '/api/v2/safety-tuning';

export function useSafetyAutotuning(): UseSafetyAutotuningReturn {
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle');
  const [lastCycleAt, setLastCycleAt] = useState<string | null>(null);
  const [gates, setGates] = useState<GateStatus[]>([]);
  const [frozenGates, setFrozenGates] = useState<string[]>([]);
  const [activeCanaries, setActiveCanaries] = useState<string[]>([]);
  const [currentCycle, setCurrentCycle] = useState<TuningCycle | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);

  const refreshStatus = useCallback(async () => {
    setStatus('loading');
    try {
      const response = await fetch(`${API_BASE}/status`);
      if (!response.ok) throw new Error('Failed to fetch status');
      
      const data = await response.json();
      setLastCycleAt(data.last_cycle_at);
      setGates(data.gates || []);
      setFrozenGates(data.frozen_gates || []);
      setActiveCanaries(data.active_canaries || []);
      setStatus('idle');
    } catch (error) {
      console.error('Error fetching safety tuning status:', error);
      setStatus('error');
    }
  }, []);

  const runCycle = useCallback(async (mode: 'propose' | 'dry-run' = 'propose'): Promise<TuningCycle | null> => {
    setStatus('loading');
    try {
      const response = await fetch(`${API_BASE}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      });
      
      if (!response.ok) throw new Error('Failed to run cycle');
      
      const data = await response.json();
      const cycle: TuningCycle = {
        cycleId: data.cycle_id,
        proposals: data.proposals.map((p: any) => ({
          proposalId: p.proposal_id,
          gateName: p.gate_name,
          currentValue: p.current_value,
          proposedValue: p.proposed_value,
          adjustmentPercent: p.adjustment_percent,
          riskLevel: p.risk_level,
          reason: p.reason,
          blockedByVolume: p.blocked_by_volume,
        })),
        proposalsCount: data.proposals_count,
        timestamp: data.timestamp,
      };
      
      setCurrentCycle(cycle);
      setStatus('idle');
      return cycle;
    } catch (error) {
      console.error('Error running tuning cycle:', error);
      setStatus('error');
      return null;
    }
  }, []);

  const applyProposal = useCallback(async (proposalId: string, auto: boolean = false): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/${proposalId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto }),
      });
      
      if (!response.ok) return false;
      
      const data = await response.json();
      return data.applied;
    } catch (error) {
      console.error('Error applying proposal:', error);
      return false;
    }
  }, []);

  const revertProposal = useCallback(async (proposalId: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/${proposalId}/revert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      
      if (!response.ok) return false;
      
      const data = await response.json();
      return data.reverted;
    } catch (error) {
      console.error('Error reverting proposal:', error);
      return false;
    }
  }, []);

  const freezeGate = useCallback(async (gateName: string, reason: string = 'manual'): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/gates/${gateName}/freeze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      
      if (!response.ok) return false;
      
      await refreshStatus();
      return true;
    } catch (error) {
      console.error('Error freezing gate:', error);
      return false;
    }
  }, [refreshStatus]);

  const unfreezeGate = useCallback(async (gateName: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/gates/${gateName}/unfreeze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      
      if (!response.ok) return false;
      
      await refreshStatus();
      return true;
    } catch (error) {
      console.error('Error unfreezing gate:', error);
      return false;
    }
  }, [refreshStatus]);

  const refreshAudit = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/audit`);
      if (!response.ok) throw new Error('Failed to fetch audit');
      
      const data = await response.json();
      setAudit(data.cycles || []);
    } catch (error) {
      console.error('Error fetching audit:', error);
    }
  }, []);

  // Load initial status
  useEffect(() => {
    refreshStatus();
    refreshAudit();
  }, [refreshStatus, refreshAudit]);

  return {
    status,
    lastCycleAt,
    gates,
    frozenGates,
    activeCanaries,
    currentCycle,
    audit,
    refreshStatus,
    runCycle,
    applyProposal,
    revertProposal,
    freezeGate,
    unfreezeGate,
    refreshAudit,
  };
}
