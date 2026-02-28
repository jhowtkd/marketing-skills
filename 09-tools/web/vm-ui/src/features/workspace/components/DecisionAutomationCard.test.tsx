/**
 * DecisionAutomationCard.test.tsx
 * 
 * Testes para o card "Automação de Decisão" no Control Center.
 * 
 * Features testadas:
 * - Status do safety gate
 * - Preview dry-run
 * - Botão "Executar com safety gates"
 * - Badge "Canary ativo"
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DecisionAutomationCard } from './DecisionAutomationCard';
import { useDecisionAutomation } from '../hooks/useDecisionAutomation';

// Mock do hook
vi.mock('../hooks/useDecisionAutomation');

const mockUseDecisionAutomation = useDecisionAutomation as jest.MockedFunction<typeof useDecisionAutomation>;

describe('DecisionAutomationCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Renderização Básica', () => {
    it('renderiza título do card', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'idle',
        safetyStatus: null,
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Automação de Decisão')).toBeInTheDocument();
    });

    it('renderiza segment key', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'idle',
        safetyStatus: null,
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('brand1:awareness')).toBeInTheDocument();
    });
  });

  describe('Status do Safety Gate', () => {
    it('mostra status VERDE quando todos gates passam', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'ready',
        safetyStatus: {
          allowed: true,
          riskLevel: 'low',
          blockedBy: [],
        },
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Safety Gates: OK')).toBeInTheDocument();
      expect(screen.getByTestId('safety-status')).toHaveClass('status-ok');
    });

    it('mostra status AMARELO quando gates bloqueiam com medium risk', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'blocked',
        safetyStatus: {
          allowed: false,
          riskLevel: 'medium',
          blockedBy: ['cooldown_active'],
        },
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Safety Gates: Bloqueado')).toBeInTheDocument();
      expect(screen.getByText('Aguardar cooldown')).toBeInTheDocument();
      expect(screen.getByTestId('safety-status')).toHaveClass('status-warning');
    });

    it('mostra status VERMELHO quando gates bloqueiam com high/critical risk', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'blocked',
        safetyStatus: {
          allowed: false,
          riskLevel: 'critical',
          blockedBy: ['regression_detected'],
        },
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Safety Gates: Bloqueado')).toBeInTheDocument();
      expect(screen.getByText('Regressão detectada')).toBeInTheDocument();
      expect(screen.getByTestId('safety-status')).toHaveClass('status-error');
    });

    it('lista todos os gates bloqueantes', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'blocked',
        safetyStatus: {
          allowed: false,
          riskLevel: 'high',
          blockedBy: ['insufficient_sample_size', 'confidence_below_threshold'],
        },
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('insufficient_sample_size')).toBeInTheDocument();
      expect(screen.getByText('confidence_below_threshold')).toBeInTheDocument();
    });
  });

  describe('Preview Dry-Run', () => {
    it('chama simulate ao clicar em "Preview"', async () => {
      const mockSimulate = vi.fn().mockResolvedValue({
        wouldExecute: true,
        predictedDecision: 'expand',
      });

      mockUseDecisionAutomation.mockReturnValue({
        status: 'idle',
        safetyStatus: null,
        canaryActive: false,
        simulate: mockSimulate,
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      fireEvent.click(screen.getByText('Preview'));
      
      await waitFor(() => {
        expect(mockSimulate).toHaveBeenCalled();
      });
    });

    it('mostra resultado do preview quando disponível', async () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'preview_ready',
        safetyStatus: { allowed: true, riskLevel: 'low', blockedBy: [] },
        preview: {
          wouldExecute: true,
          predictedDecision: 'expand',
          confidence: 0.85,
        },
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Decisão prevista: expand')).toBeInTheDocument();
      expect(screen.getByText('Confiança: 85%')).toBeInTheDocument();
    });
  });

  describe('Botão Executar', () => {
    it('habilita botão quando safety gates passam', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'ready',
        safetyStatus: { allowed: true, riskLevel: 'low', blockedBy: [] },
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      const button = screen.getByText('Executar com safety gates');
      expect(button).toBeEnabled();
    });

    it('desabilita botão quando safety gates bloqueiam', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'blocked',
        safetyStatus: { allowed: false, riskLevel: 'high', blockedBy: ['insufficient_sample'] },
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      const button = screen.getByText('Executar com safety gates');
      expect(button).toBeDisabled();
    });

    it('chama execute ao clicar no botão', async () => {
      const mockExecute = vi.fn().mockResolvedValue({ status: 'completed' });

      mockUseDecisionAutomation.mockReturnValue({
        status: 'ready',
        safetyStatus: { allowed: true, riskLevel: 'low', blockedBy: [] },
        canaryActive: false,
        simulate: vi.fn(),
        execute: mockExecute,
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      fireEvent.click(screen.getByText('Executar com safety gates'));
      
      await waitFor(() => {
        expect(mockExecute).toHaveBeenCalled();
      });
    });
  });

  describe('Badge Canary', () => {
    it('mostra badge "Canary Ativo" quando canary está rodando', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'canary_running',
        safetyStatus: { allowed: true, riskLevel: 'low', blockedBy: [] },
        canaryActive: true,
        canaryStatus: {
          subsetPercentage: 10,
          observationTimeRemaining: 15,
        },
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Canary Ativo')).toBeInTheDocument();
      expect(screen.getByText('10% subset')).toBeInTheDocument();
      expect(screen.getByText('15 min restantes')).toBeInTheDocument();
    });

    it('não mostra badge quando canary não está ativo', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'ready',
        safetyStatus: { allowed: true, riskLevel: 'low', blockedBy: [] },
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.queryByText('Canary Ativo')).not.toBeInTheDocument();
    });

    it('mostra status "Promovido" quando canary é promovido', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'canary_promoted',
        safetyStatus: { allowed: true, riskLevel: 'low', blockedBy: [] },
        canaryActive: false,
        canaryResult: { status: 'promoted', successRate: 0.98 },
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Canary Promovido')).toBeInTheDocument();
      expect(screen.getByText('98% sucesso')).toBeInTheDocument();
    });

    it('mostra status "Abortado" quando canary é abortado', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'canary_aborted',
        safetyStatus: { allowed: true, riskLevel: 'low', blockedBy: [] },
        canaryActive: false,
        canaryResult: { status: 'aborted', successRate: 0.72 },
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Canary Abortado')).toBeInTheDocument();
      expect(screen.getByText('72% sucesso - abaixo do threshold')).toBeInTheDocument();
    });
  });

  describe('Estados de Loading', () => {
    it('mostra spinner durante simulação', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'simulating',
        safetyStatus: null,
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: true,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('mostra spinner durante execução', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'executing',
        safetyStatus: { allowed: true, riskLevel: 'low', blockedBy: [] },
        canaryActive: false,
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: true,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Executando...')).toBeInTheDocument();
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });
  });

  describe('Estados de Rollback', () => {
    it('mostra alerta quando rollback é acionado', () => {
      mockUseDecisionAutomation.mockReturnValue({
        status: 'rollback_triggered',
        safetyStatus: { allowed: true, riskLevel: 'critical', blockedBy: ['regression'] },
        canaryActive: false,
        rollbackInfo: {
          triggered: true,
          reason: 'Post-execution regression detected',
          triggeredAt: '2026-02-28T10:00:00Z',
        },
        simulate: vi.fn(),
        execute: vi.fn(),
        isLoading: false,
      });

      render(<DecisionAutomationCard segmentKey="brand1:awareness" />);
      
      expect(screen.getByText('Rollback Acionado')).toBeInTheDocument();
      expect(screen.getByText('Post-execution regression detected')).toBeInTheDocument();
    });
  });
});
