/**
 * useWorkspace.decisionAutomation.test.tsx
 * 
 * Testes de integração para o hook useDecisionAutomation no contexto do workspace.
 */

import { describe, it, expect } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useDecisionAutomation } from './hooks/useDecisionAutomation';

describe('useDecisionAutomation', () => {
  it('inicia com status idle', () => {
    const { result } = renderHook(() => useDecisionAutomation('brand1:awareness'));
    
    expect(result.current.status).toBe('idle');
    expect(result.current.isLoading).toBe(false);
    expect(result.current.safetyStatus).toBeNull();
  });

  it('simula e atualiza status para preview_ready', async () => {
    const { result } = renderHook(() => useDecisionAutomation('brand1:awareness'));
    
    act(() => {
      result.current.simulate();
    });
    
    expect(result.current.status).toBe('simulating');
    expect(result.current.isLoading).toBe(true);
    
    await waitFor(() => {
      expect(result.current.status).toBe('preview_ready');
    });
    
    expect(result.current.safetyStatus).not.toBeNull();
    expect(result.current.preview).not.toBeNull();
  });

  it('executa e inicia canary', async () => {
    const { result } = renderHook(() => useDecisionAutomation('brand1:awareness'));
    
    await act(async () => {
      await result.current.execute();
    });
    
    expect(result.current.status).toBe('canary_running');
    expect(result.current.canaryActive).toBe(true);
    expect(result.current.canaryStatus).not.toBeNull();
  });
});
