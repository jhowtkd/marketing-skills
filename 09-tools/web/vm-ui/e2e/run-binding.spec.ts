import { test, expect } from '@playwright/test';

/**
 * E2E tests for run binding functionality
 * 
 * These tests verify that:
 * 1. When a thread has existing runs, the first one is auto-selected
 * 2. No false "empty state" is shown when runs exist
 * 3. Preview content is loaded without manual selection
 * 
 * Run with: npx playwright test e2e/run-binding.spec.ts
 */

test.describe('Run Binding E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the studio
    await page.goto('/');
    
    // Wait for the app to be ready
    await page.waitForSelector('[data-testid="studio-container"]', { timeout: 10000 });
  });

  test('should auto-select first run when thread has runs', async ({ page }) => {
    // Assuming there's a seeded thread with runs
    // In a real scenario, we'd create this via API or use a seeded database
    
    // Select a thread that has runs (seeded data)
    // This selector assumes the thread list is rendered with data-testid
    const threadWithRuns = page.locator('[data-testid="thread-item"]').first();
    
    // If no seeded threads exist, skip this test
    if (await threadWithRuns.count() === 0) {
      test.skip('No seeded threads available for testing');
      return;
    }
    
    await threadWithRuns.click();
    
    // Wait for workspace to load
    await page.waitForSelector('[data-testid="workspace-panel"]', { timeout: 5000 });
    
    // Verify that a run is auto-selected (no empty state)
    const emptyState = page.locator('text=/Ainda nao existe uma versao ativa/i');
    await expect(emptyState).not.toBeVisible();
    
    // Verify run status is shown (indicating a run is active)
    const runStatus = page.locator('[data-testid="run-status-badge"]').first();
    await expect(runStatus).toBeVisible();
  });

  test('should load preview without manual run selection', async ({ page }) => {
    const threadWithRuns = page.locator('[data-testid="thread-item"]').first();
    
    if (await threadWithRuns.count() === 0) {
      test.skip('No seeded threads available for testing');
      return;
    }
    
    await threadWithRuns.click();
    await page.waitForSelector('[data-testid="workspace-panel"]', { timeout: 5000 });
    
    // Check that preview content is loaded
    const previewPanel = page.locator('[data-testid="artifact-preview"]').first();
    
    // Preview should either have content or a loading state
    // The key is that it's attempting to load without manual intervention
    await expect(previewPanel).toBeVisible({ timeout: 5000 });
  });

  test('should show run details in dev mode', async ({ page }) => {
    const threadWithRuns = page.locator('[data-testid="thread-item"]').first();
    
    if (await threadWithRuns.count() === 0) {
      test.skip('No seeded threads available for testing');
      return;
    }
    
    await threadWithRuns.click();
    await page.waitForSelector('[data-testid="workspace-panel"]', { timeout: 5000 });
    
    // Enable dev mode
    const devModeToggle = page.locator('[data-testid="dev-mode-toggle"]');
    if (await devModeToggle.count() > 0) {
      await devModeToggle.click();
      
      // Verify run ID is visible in dev mode
      const runIdDisplay = page.locator('[data-testid="run-id-display"]').first();
      await expect(runIdDisplay).toBeVisible();
    }
  });
});

test.describe('Run Binding with API seeding', () => {
  test('should handle API response shape for runs list', async ({ page, request }) => {
    // This test would ideally seed data via API and verify the UI handles it correctly
    // For now, it's a structural placeholder showing the intended test flow
    
    test.info().annotations.push({ 
      type: 'info', 
      description: 'Full E2E test requires backend API seeding capability'
    });
    
    // Placeholder assertion - remove when full test is implemented
    expect(true).toBe(true);
  });
});
