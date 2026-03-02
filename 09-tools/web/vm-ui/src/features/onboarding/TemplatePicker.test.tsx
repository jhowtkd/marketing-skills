import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TemplatePicker } from './TemplatePicker';
import type { Template } from './templates';

// Mock telemetry
vi.mock('./telemetry', () => ({
  trackTimeToFirstValue: vi.fn(),
}));

describe('TemplatePicker', () => {
  const mockOnSelect = vi.fn();
  const mockOnCancel = vi.fn();

  const mockTemplates: Template[] = [
    {
      id: 'blog-post',
      name: 'Blog Post',
      description: 'Create engaging blog content',
      category: 'content',
      icon: '📝',
      defaultPrompt: 'Write a blog post about...',
    },
    {
      id: 'landing-page',
      name: 'Landing Page',
      description: 'High-converting landing page copy',
      category: 'conversion',
      icon: '🎯',
      defaultPrompt: 'Create landing page copy for...',
    },
    {
      id: 'social-media',
      name: 'Social Media',
      description: 'Engaging social media posts',
      category: 'social',
      icon: '📱',
      defaultPrompt: 'Write a social media post about...',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('should render template grid', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByText(/escolha um template/i)).toBeInTheDocument();
      expect(screen.getByText('Blog Post')).toBeInTheDocument();
      expect(screen.getByText('Landing Page')).toBeInTheDocument();
      expect(screen.getByText('Social Media')).toBeInTheDocument();
    });

    it('should show template descriptions', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByText('Create engaging blog content')).toBeInTheDocument();
      expect(screen.getByText('High-converting landing page copy')).toBeInTheDocument();
    });

    it('should show icons for templates', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
        />
      );

      expect(screen.getByText('📝')).toBeInTheDocument();
      expect(screen.getByText('🎯')).toBeInTheDocument();
      expect(screen.getByText('📱')).toBeInTheDocument();
    });
  });

  describe('selection', () => {
    it('should call onSelect when clicking a template', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
        />
      );

      const templateCard = screen.getByText('Blog Post').closest('button');
      fireEvent.click(templateCard!);

      expect(mockOnSelect).toHaveBeenCalledWith('blog-post', expect.any(Object));
    });

    it('should highlight selected template', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
          selectedTemplateId="blog-post"
        />
      );

      const selectedCard = screen.getByText('Blog Post').closest('button');
      expect(selectedCard).toHaveClass('ring-2');
    });

    it('should show prefill preview when template selected', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
          selectedTemplateId="blog-post"
        />
      );

      expect(screen.getByText(/pré-visualização/i)).toBeInTheDocument();
      expect(screen.getByText('Write a blog post about...')).toBeInTheDocument();
    });
  });

  describe('filtering', () => {
    it('should filter templates by category', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
        />
      );

      const categorySelect = screen.getByLabelText(/categoria/i);
      fireEvent.change(categorySelect, { target: { value: 'content' } });

      expect(screen.getByText('Blog Post')).toBeInTheDocument();
      expect(screen.queryByText('Landing Page')).not.toBeInTheDocument();
    });

    it('should show all templates when selecting "all" category', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
        />
      );

      const categorySelect = screen.getByLabelText(/categoria/i);
      fireEvent.change(categorySelect, { target: { value: 'all' } });

      expect(screen.getByText('Blog Post')).toBeInTheDocument();
      expect(screen.getByText('Landing Page')).toBeInTheDocument();
      expect(screen.getByText('Social Media')).toBeInTheDocument();
    });
  });

  describe('search', () => {
    it('should filter templates by search query', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
        />
      );

      const searchInput = screen.getByPlaceholderText(/buscar templates/i);
      fireEvent.change(searchInput, { target: { value: 'blog' } });

      expect(screen.getByText('Blog Post')).toBeInTheDocument();
      expect(screen.queryByText('Landing Page')).not.toBeInTheDocument();
    });

    it('should show empty state when no templates match', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
        />
      );

      const searchInput = screen.getByPlaceholderText(/buscar templates/i);
      fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

      expect(screen.getByText(/nenhum template encontrado/i)).toBeInTheDocument();
    });
  });

  describe('cancel', () => {
    it('should call onCancel when clicking cancel button', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
        />
      );

      const cancelButton = screen.getByRole('button', { name: /cancelar/i });
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalled();
    });
  });

  describe('first success suggestions', () => {
    it('should highlight recommended template', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
          recommendedTemplateId="blog-post"
        />
      );

      expect(screen.getByText(/recomendado/i)).toBeInTheDocument();
    });

    it('should show first success badge on recommended template', () => {
      render(
        <TemplatePicker
          templates={mockTemplates}
          onSelect={mockOnSelect}
          onCancel={mockOnCancel}
          recommendedTemplateId="blog-post"
        />
      );

      const badge = screen.getByText(/1º valor/i);
      expect(badge).toBeInTheDocument();
    });
  });
});
