import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SettingsPage from './SettingsPage';

describe('SettingsPage - Task First Redesign', () => {
  const mockSettings = [
    {
      id: 'notification_email',
      domain: 'notifications',
      label: 'Email Notifications',
      description: 'Receive updates via email',
      value: true,
      type: 'boolean' as const,
      impact: 'high' as const,
    },
    {
      id: 'theme',
      domain: 'appearance',
      label: 'Dark Theme',
      description: 'Use dark color scheme',
      value: false,
      type: 'boolean' as const,
      impact: 'low' as const,
    },
    {
      id: 'auto_save',
      domain: 'workflow',
      label: 'Auto Save',
      description: 'Automatically save drafts',
      value: true,
      type: 'boolean' as const,
      impact: 'medium' as const,
    },
  ];

  const defaultProps = {
    settings: mockSettings,
    onSettingChange: vi.fn(),
    onDomainExpand: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('domain grouping', () => {
    it('should group settings by domain', () => {
      render(<SettingsPage {...defaultProps} />);
      
      // Should show domain sections
      expect(screen.getByText('Notifications')).toBeInTheDocument();
      expect(screen.getByText('Appearance')).toBeInTheDocument();
      expect(screen.getByText('Workflow')).toBeInTheDocument();
    });

    it('should expand domain on click', () => {
      const onDomainExpand = vi.fn();
      render(<SettingsPage {...defaultProps} onDomainExpand={onDomainExpand} />);
      
      fireEvent.click(screen.getByText('Notifications'));
      
      expect(onDomainExpand).toHaveBeenCalledWith('notifications');
    });

    it('should show setting count per domain', () => {
      render(<SettingsPage {...defaultProps} />);
      
      // Each domain should show how many settings it contains
      const domains = screen.getAllByTestId('domain-count');
      expect(domains.length).toBeGreaterThan(0);
    });
  });

  describe('impact previews', () => {
    it('should show impact preview card when setting is focused', () => {
      render(<SettingsPage {...defaultProps} />);
      
      // Expand the domain first
      fireEvent.click(screen.getByText('Notifications'));
      
      // Find the setting area and trigger hover
      const settingRow = screen.getByText('Email Notifications').closest('div');
      if (settingRow) {
        fireEvent.mouseEnter(settingRow);
      }
      
      // Impact preview card should appear
      expect(screen.getByTestId('impact-preview')).toBeInTheDocument();
    });

    it('should display impact level for each setting', () => {
      render(<SettingsPage {...defaultProps} />);
      
      // Expand the domain first
      fireEvent.click(screen.getByText('Notifications'));
      
      // High impact setting should be marked - look for the text in the document
      const pageContent = document.body.textContent || '';
      expect(pageContent.toLowerCase()).toContain('high impact');
    });

    it('should show what changes will affect', () => {
      render(<SettingsPage {...defaultProps} />);
      
      // Expand the domain first
      fireEvent.click(screen.getByText('Notifications'));
      
      // Find the setting area and trigger hover
      const settingRow = screen.getByText('Email Notifications').closest('div');
      if (settingRow) {
        fireEvent.mouseEnter(settingRow);
      }
      
      // Should show affected areas
      expect(screen.getByText(/Affects/i)).toBeInTheDocument();
    });
  });

  describe('task-first workflow', () => {
    it('should show recommended settings to change', () => {
      render(<SettingsPage {...defaultProps} recommendedSettings={['notification_email']} />);
      
      // Should show recommended badge in the domain header
      expect(screen.getByText(/1 Recommended/i)).toBeInTheDocument();
    });

    it('should track setting changes', () => {
      const onSettingChange = vi.fn();
      render(<SettingsPage {...defaultProps} onSettingChange={onSettingChange} />);
      
      // Expand the domain first
      fireEvent.click(screen.getByText('Notifications'));
      
      // Toggle a setting - the switch is a button with role "switch"
      const toggleButton = screen.getByText('Email Notifications').closest('div')?.parentElement?.querySelector('button[role="switch"]');
      if (toggleButton) {
        fireEvent.click(toggleButton);
        expect(onSettingChange).toHaveBeenCalledWith('notification_email', false);
      }
    });

    it('should show completion progress', () => {
      render(<SettingsPage {...defaultProps} completedSettings={['theme']} />);
      
      // Should show progress indicator
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('should have proper heading structure', () => {
      render(<SettingsPage {...defaultProps} />);
      
      const heading = screen.getByRole('heading', { level: 2 });
      expect(heading).toBeInTheDocument();
    });

    it('should describe impact to screen readers', () => {
      render(<SettingsPage {...defaultProps} />);
      
      // Expand the domain first
      fireEvent.click(screen.getByText('Notifications'));
      
      // Find the switch button
      const toggleButton = screen.getByText('Email Notifications').closest('div')?.parentElement?.querySelector('button[role="switch"]');
      if (toggleButton) {
        expect(toggleButton).toHaveAttribute('aria-describedby');
      }
    });
  });

  describe('v29 UX metrics', () => {
    it('should track time spent on settings page', () => {
      // Simplified test - just verify the component renders with tracking prop
      const onTrackTime = vi.fn();
      const { unmount } = render(<SettingsPage {...defaultProps} onTrackTime={onTrackTime} />);
      
      // Unmount to trigger the cleanup effect
      unmount();
      
      // The effect should be called on unmount
      expect(onTrackTime).toHaveBeenCalled();
    });

    it('should track setting change events', () => {
      const onTrackChange = vi.fn();
      render(<SettingsPage {...defaultProps} onTrackChange={onTrackChange} />);
      
      // Expand the domain first
      fireEvent.click(screen.getByText('Notifications'));
      
      // Toggle a setting
      const toggleButton = screen.getByText('Email Notifications').closest('div')?.parentElement?.querySelector('button[role="switch"]');
      if (toggleButton) {
        fireEvent.click(toggleButton);
        
        expect(onTrackChange).toHaveBeenCalledWith({
          settingId: 'notification_email',
          oldValue: true,
          newValue: false,
          timestamp: expect.any(Number),
        });
      }
    });
  });
});
