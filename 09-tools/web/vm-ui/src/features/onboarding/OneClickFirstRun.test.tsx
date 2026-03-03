/**
 * Tests for v38 One-Click First Run feature
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TemplatePicker } from './TemplatePicker';
import type { Template } from './templates';

// Mock templates data
const mockTemplates: Template[] = [
  {
    id: 'blog-post',
    name: 'Blog Post',
    description: 'Create engaging blog content',
    category: 'content',
    icon: '📝',
    defaultPrompt: 'Write about {topic}',
    variables: [{ name: 'topic', label: 'Topic', placeholder: 'Enter topic', required: true }],
  },
  {
    id: 'landing-page',
    name: 'Landing Page',
    description: 'High-conversion landing page copy',
    category: 'conversion',
    icon: '🎯',
    defaultPrompt: 'Create copy for {product}',
    variables: [{ name: 'product', label: 'Product', placeholder: 'Product name', required: true }],
  },
];

describe('OneClickFirstRun', () => {
  const mockOnSelect = vi.fn();
  const mockOnCancel = vi.fn();
  const mockOnFirstRunComplete = vi.fn();
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch = vi.fn();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should fetch first run recommendation on mount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        user_id: 'user-123',
        recommended_template: 'blog-post',
        one_click_ready: true,
        cta_text: 'Criar meu primeiro conteúdo',
        contextualized_params: {},
      }),
    });

    render(
      <TemplatePicker
        templates={mockTemplates}
        onSelect={mockOnSelect}
        onCancel={mockOnCancel}
        userId="user-123"
        onFirstRunComplete={mockOnFirstRunComplete}
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v2/onboarding/first-run/recommend',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('user-123'),
        })
      );
    });
  });

  it('should show one-click button when template is selected and ready', async () => {
    // First recommendation call
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        user_id: 'user-123',
        recommended_template: 'blog-post',
        one_click_ready: true,
        cta_text: 'Criar meu primeiro conteúdo',
        contextualized_params: {},
      }),
    });

    render(
      <TemplatePicker
        templates={mockTemplates}
        onSelect={mockOnSelect}
        onCancel={mockOnCancel}
        userId="user-123"
        selectedTemplateId="blog-post"
        onFirstRunComplete={mockOnFirstRunComplete}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('one-click-first-run')).toBeInTheDocument();
    });

    expect(screen.getByText(/criar meu primeiro conteúdo/i)).toBeInTheDocument();
  });

  it('should execute one-click first run on button click', async () => {
    // Recommendation call
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          user_id: 'user-123',
          recommended_template: 'blog-post',
          one_click_ready: true,
          cta_text: 'Criar meu primeiro conteúdo',
          contextualized_params: {},
        }),
      })
      // Plan call
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          user_id: 'user-123',
          template_id: 'blog-post',
          status: 'ready',
          one_click_ready: true,
          execution_steps: ['load_template', 'generate_content'],
          estimated_duration_ms: 2000,
          sanitized_params: { topic: 'Marketing' },
        }),
      })
      // Execute call
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: true,
          user_id: 'user-123',
          output: {
            title: 'Generated Blog Post: Marketing',
            preview: 'This is your first blog-post about Marketing.',
          },
          execution_time_ms: 1500,
        }),
      });

    render(
      <TemplatePicker
        templates={mockTemplates}
        onSelect={mockOnSelect}
        onCancel={mockOnCancel}
        userId="user-123"
        selectedTemplateId="blog-post"
        onFirstRunComplete={mockOnFirstRunComplete}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('one-click-first-run')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('one-click-first-run'));

    await waitFor(() => {
      expect(screen.getByTestId('one-click-result')).toBeInTheDocument();
    });

    expect(screen.getByText(/primeiro valor criado/i)).toBeInTheDocument();
    expect(mockOnFirstRunComplete).toHaveBeenCalled();
  });

  it('should show loading state during one-click execution', async () => {
    // Recommendation call
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          user_id: 'user-123',
          recommended_template: 'blog-post',
          one_click_ready: true,
          cta_text: 'Criar meu primeiro conteúdo',
        }),
      })
      // Plan call - slow to show loading
      .mockImplementationOnce(() => new Promise(resolve => setTimeout(resolve, 100)));

    render(
      <TemplatePicker
        templates={mockTemplates}
        onSelect={mockOnSelect}
        onCancel={mockOnCancel}
        userId="user-123"
        selectedTemplateId="blog-post"
        onFirstRunComplete={mockOnFirstRunComplete}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('one-click-first-run')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('one-click-first-run'));

    // Should show loading state
    await waitFor(() => {
      expect(screen.getByText(/gerando/i)).toBeInTheDocument();
    });
  });

  it('should handle one-click execution failure', async () => {
    // Recommendation call
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          user_id: 'user-123',
          recommended_template: 'blog-post',
          one_click_ready: true,
          cta_text: 'Criar meu primeiro conteúdo',
        }),
      })
      // Plan call
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          user_id: 'user-123',
          template_id: 'blog-post',
          status: 'ready',
          one_click_ready: true,
        }),
      })
      // Execute call fails
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          success: false,
          user_id: 'user-123',
          error: 'Generation failed',
          fallback_options: ['try_again', 'manual_input'],
        }),
      });

    render(
      <TemplatePicker
        templates={mockTemplates}
        onSelect={mockOnSelect}
        onCancel={mockOnCancel}
        userId="user-123"
        selectedTemplateId="blog-post"
        onFirstRunComplete={mockOnFirstRunComplete}
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('one-click-first-run')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('one-click-first-run'));

    await waitFor(() => {
      expect(screen.getByTestId('one-click-result')).toBeInTheDocument();
    });

    expect(screen.getByText(/generation failed/i)).toBeInTheDocument();
  });

  it('should not show one-click button when not ready', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        user_id: 'user-123',
        recommended_template: 'blog-post',
        one_click_ready: false,
        fallback_template: 'blog-post',
        reason: 'Missing parameters',
      }),
    });

    render(
      <TemplatePicker
        templates={mockTemplates}
        onSelect={mockOnSelect}
        onCancel={mockOnCancel}
        userId="user-123"
        selectedTemplateId="blog-post"
      />
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // One-click button should not be present
    expect(screen.queryByTestId('one-click-first-run')).not.toBeInTheDocument();
  });

  it('should gracefully handle recommendation fetch failure', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    render(
      <TemplatePicker
        templates={mockTemplates}
        onSelect={mockOnSelect}
        onCancel={mockOnCancel}
        userId="user-123"
        selectedTemplateId="blog-post"
      />
    );

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to fetch first run recommendation:',
        expect.any(Error)
      );
    });

    // Template picker should still work
    expect(screen.getByText(/escolha um template/i)).toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});
