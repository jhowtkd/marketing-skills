import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ApprovalLearningOpsPanel } from './ApprovalLearningOpsPanel';

// Mock fetch
global.fetch = vi.fn();

describe('ApprovalLearningOpsPanel', () => {
  const defaultProps = {
    brandId: 'brand-001',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders component with title', () => {
    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'active', version: 'v24' }),
    });

    render(<ApprovalLearningOpsPanel {...defaultProps} />);
    expect(screen.getByText(/Approval Learning Ops/i)).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    (fetch as any).mockImplementation(() => new Promise(() => {}));

    render(<ApprovalLearningOpsPanel {...defaultProps} />);
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });

  it('shows empty state when no proposals', async () => {
    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({ status: 'active', version: 'v24', proposals: [], history: [] }),
    });

    render(<ApprovalLearningOpsPanel {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText(/No pending suggestions/i)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('handles freeze action when clicked', async () => {
    (fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'active', version: 'v24' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ proposals: [], count: 0 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ brand_id: 'brand-001', history: [], count: 0 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ frozen: true, brand_id: 'brand-001' }),
      });

    render(<ApprovalLearningOpsPanel {...defaultProps} />);

    // Wait for buttons to appear
    await waitFor(() => {
      const buttons = screen.queryAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    const freezeButton = screen.getByText(/Freeze Learning/i);
    fireEvent.click(freezeButton);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/brands/brand-001/freeze'),
        expect.objectContaining({ method: 'POST' })
      );
    });
  });
});
