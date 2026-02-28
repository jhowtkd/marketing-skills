import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AlertPanel } from "./AlertPanel";
import type { Alert, PlaybookExecutionResult } from "../hooks/useAlerts";

const mockExecutePlaybookChain = vi.fn();

const createMockAlert = (overrides: Partial<Alert> = {}): Alert => ({
  alert_id: overrides.alert_id || "alert-1",
  severity: overrides.severity || "warning",
  cause: overrides.cause || "TEST_CAUSE",
  recommendation: overrides.recommendation || "Test recommendation",
  created_at: overrides.created_at || "2026-02-27T10:00:00Z",
  updated_at: overrides.updated_at || "2026-02-27T10:00:00Z",
  ...overrides,
});

describe("AlertPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockExecutePlaybookChain.mockResolvedValue({
      status: "success",
      executed: ["step-1"],
      skipped: [],
      errors: [],
    } as PlaybookExecutionResult);
  });

  describe("Loading state", () => {
    it("should display loading indicator when loading is true", () => {
      render(<AlertPanel alerts={[]} loading={true} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.getByTestId("alerts-loading")).toBeInTheDocument();
      expect(screen.getByText(/carregando alertas/i)).toBeInTheDocument();
    });

    it("should not display alerts list when loading", () => {
      const alerts = [createMockAlert()];
      render(<AlertPanel alerts={alerts} loading={true} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.queryByTestId("alerts-list")).not.toBeInTheDocument();
    });
  });

  describe("Error state", () => {
    it("should display error message when error is present", () => {
      render(
        <AlertPanel alerts={[]} loading={false} error="Failed to load" onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />
      );

      expect(screen.getByTestId("alerts-error")).toBeInTheDocument();
      expect(screen.getByText(/Failed to load/)).toBeInTheDocument();
    });

    it("should display refresh button in error state", () => {
      const onRefresh = vi.fn();
      render(<AlertPanel alerts={[]} loading={false} error="Error" onRefresh={onRefresh} onExecutePlaybook={mockExecutePlaybookChain} />);

      const refreshButton = screen.getByTestId("alerts-refresh-btn");
      expect(refreshButton).toBeInTheDocument();

      fireEvent.click(refreshButton);
      expect(onRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe("Empty state", () => {
    it("should display empty state when no alerts and not loading", () => {
      render(<AlertPanel alerts={[]} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.getByTestId("alerts-empty")).toBeInTheDocument();
      expect(screen.getByText(/nenhum alerta ativo/i)).toBeInTheDocument();
    });

    it("should display refresh button in empty state", () => {
      const onRefresh = vi.fn();
      render(<AlertPanel alerts={[]} loading={false} error={null} onRefresh={onRefresh} onExecutePlaybook={mockExecutePlaybookChain} />);

      const refreshButton = screen.getByTestId("alerts-refresh-btn");
      fireEvent.click(refreshButton);
      expect(onRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe("Alerts list display", () => {
    it("should display alerts list when alerts are provided", () => {
      const alerts = [createMockAlert({ alert_id: "alert-1", cause: "API_FAILURE" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.getByTestId("alerts-list")).toBeInTheDocument();
      expect(screen.getByText("API_FAILURE")).toBeInTheDocument();
    });

    it("should display multiple alerts", () => {
      const alerts = [
        createMockAlert({ alert_id: "alert-1", cause: "ERROR_1" }),
        createMockAlert({ alert_id: "alert-2", cause: "ERROR_2" }),
        createMockAlert({ alert_id: "alert-3", cause: "ERROR_3" }),
      ];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.getByText("ERROR_1")).toBeInTheDocument();
      expect(screen.getByText("ERROR_2")).toBeInTheDocument();
      expect(screen.getByText("ERROR_3")).toBeInTheDocument();
    });

    it("should display alert severity badges", () => {
      const alerts = [
        createMockAlert({ alert_id: "1", severity: "critical" }),
        createMockAlert({ alert_id: "2", severity: "warning" }),
        createMockAlert({ alert_id: "3", severity: "info" }),
      ];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.getByTestId("severity-critical")).toBeInTheDocument();
      expect(screen.getByTestId("severity-warning")).toBeInTheDocument();
      expect(screen.getByTestId("severity-info")).toBeInTheDocument();
    });

    it("should display alert cause", () => {
      const alerts = [createMockAlert({ cause: "DATABASE_CONNECTION_FAILED" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.getByText("DATABASE_CONNECTION_FAILED")).toBeInTheDocument();
    });

    it("should display alert recommendation", () => {
      const alerts = [createMockAlert({ recommendation: "Check database connection and retry" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.getByText("Check database connection and retry")).toBeInTheDocument();
    });

    it("should display formatted timestamps", () => {
      const alerts = [createMockAlert({ created_at: "2026-02-27T10:30:00Z", updated_at: "2026-02-27T11:00:00Z" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      // Should display formatted dates
      expect(screen.getByText(/27.*02.*2026/)).toBeInTheDocument();
    });
  });

  describe("Severity styling", () => {
    it("should apply critical severity styling", () => {
      const alerts = [createMockAlert({ severity: "critical" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      const alertElement = screen.getByTestId("alert-item-alert-1");
      expect(alertElement.className).toMatch(/critical|red|danger/i);
    });

    it("should apply warning severity styling", () => {
      const alerts = [createMockAlert({ severity: "warning" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      const alertElement = screen.getByTestId("alert-item-alert-1");
      expect(alertElement.className).toMatch(/warning|yellow|orange/i);
    });

    it("should apply info severity styling", () => {
      const alerts = [createMockAlert({ severity: "info" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      const alertElement = screen.getByTestId("alert-item-alert-1");
      expect(alertElement.className).toMatch(/info|blue/i);
    });
  });

  describe("Execute playbook chain CTA", () => {
    it("should display execute button for alerts with playbook chain", () => {
      const alerts = [createMockAlert({ playbook_chain_id: "chain-1" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.getByTestId("execute-playbook-btn-alert-1")).toBeInTheDocument();
    });

    it("should not display execute button when no playbook_chain_id", () => {
      const alerts = [createMockAlert({ playbook_chain_id: undefined })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.queryByTestId(/execute-playbook-btn/)).not.toBeInTheDocument();
    });

    it("should call onExecutePlaybook when execute button is clicked", async () => {
      const alerts = [createMockAlert({ alert_id: "alert-1", playbook_chain_id: "chain-1" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      const executeButton = screen.getByTestId("execute-playbook-btn-alert-1");
      fireEvent.click(executeButton);

      await waitFor(() => {
        expect(mockExecutePlaybookChain).toHaveBeenCalledWith("chain-1");
      });
    });

    it("should show loading state on execute button during execution", async () => {
      // Create a delayed promise to keep loading state
      let resolveExecution: (value: PlaybookExecutionResult) => void;
      const executionPromise = new Promise<PlaybookExecutionResult>((resolve) => {
        resolveExecution = resolve;
      });
      mockExecutePlaybookChain.mockReturnValue(executionPromise);

      const alerts = [createMockAlert({ alert_id: "alert-1", playbook_chain_id: "chain-1" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      const executeButton = screen.getByTestId("execute-playbook-btn-alert-1");
      fireEvent.click(executeButton);

      // Button should show loading state
      await waitFor(() => {
        expect(screen.getByTestId("playbook-executing-alert-1")).toBeInTheDocument();
      });

      // Resolve the promise
      resolveExecution!({ status: "success", executed: [], skipped: [], errors: [] });
    });

    it("should display execution feedback after successful execution", async () => {
      mockExecutePlaybookChain.mockResolvedValue({
        status: "success",
        executed: ["step-1", "step-2"],
        skipped: ["step-3"],
        errors: [],
      } as PlaybookExecutionResult);

      const alerts = [createMockAlert({ alert_id: "alert-1", playbook_chain_id: "chain-1" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      const executeButton = screen.getByTestId("execute-playbook-btn-alert-1");
      fireEvent.click(executeButton);

      await waitFor(() => {
        expect(screen.getByTestId("execution-feedback-alert-1")).toBeInTheDocument();
      });

      expect(screen.getByText(/executado com sucesso/i)).toBeInTheDocument();
      expect(screen.getByText(/2 passos executados/i)).toBeInTheDocument();
    });

    it("should display execution errors when playbook fails", async () => {
      mockExecutePlaybookChain.mockResolvedValue({
        status: "partial",
        executed: ["step-1"],
        skipped: [],
        errors: [{ step: "step-2", error: "Connection timeout" }],
      } as PlaybookExecutionResult);

      const alerts = [createMockAlert({ alert_id: "alert-1", playbook_chain_id: "chain-1" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      const executeButton = screen.getByTestId("execute-playbook-btn-alert-1");
      fireEvent.click(executeButton);

      await waitFor(() => {
        expect(screen.getByTestId("execution-error-alert-1")).toBeInTheDocument();
      });

      expect(screen.getByText(/Connection timeout/)).toBeInTheDocument();
    });

    it("should handle execution exception", async () => {
      mockExecutePlaybookChain.mockRejectedValue(new Error("Network error during execution"));

      const alerts = [createMockAlert({ alert_id: "alert-1", playbook_chain_id: "chain-1" })];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      const executeButton = screen.getByTestId("execute-playbook-btn-alert-1");
      fireEvent.click(executeButton);

      await waitFor(() => {
        expect(screen.getByTestId("execution-error-alert-1")).toBeInTheDocument();
      });

      expect(screen.getByText(/Network error during execution/)).toBeInTheDocument();
    });
  });

  describe("Manual refresh", () => {
    it("should call onRefresh when refresh button is clicked in normal state", () => {
      const onRefresh = vi.fn();
      const alerts = [createMockAlert()];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={onRefresh} onExecutePlaybook={mockExecutePlaybookChain} />);

      const refreshButton = screen.getByTestId("alerts-refresh-btn");
      fireEvent.click(refreshButton);

      expect(onRefresh).toHaveBeenCalledTimes(1);
    });

    it("should disable refresh button while loading", () => {
      const onRefresh = vi.fn();

      render(<AlertPanel alerts={[]} loading={true} error={null} onRefresh={onRefresh} onExecutePlaybook={mockExecutePlaybookChain} />);

      const refreshButton = screen.getByTestId("alerts-refresh-btn");
      expect(refreshButton).toBeDisabled();
    });
  });

  describe("Alert counts summary", () => {
    it("should display alert counts summary when alerts exist", () => {
      const alerts = [
        createMockAlert({ severity: "critical" }),
        createMockAlert({ severity: "critical" }),
        createMockAlert({ severity: "warning" }),
      ];

      render(<AlertPanel alerts={alerts} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.getByTestId("alerts-summary")).toBeInTheDocument();
      expect(screen.getByText(/3 alertas/i)).toBeInTheDocument();
      expect(screen.getByText(/2 críticos/i)).toBeInTheDocument();
      expect(screen.getByText(/1 warning/i)).toBeInTheDocument();
    });

    it("should not display summary when no alerts", () => {
      render(<AlertPanel alerts={[]} loading={false} error={null} onRefresh={vi.fn()} onExecutePlaybook={mockExecutePlaybookChain} />);

      expect(screen.queryByTestId("alerts-summary")).not.toBeInTheDocument();
    });
  });

  describe("Dismiss alert", () => {
    it("should have dismiss button for each alert", () => {
      const alerts = [createMockAlert({ alert_id: "alert-1" })];
      const onDismiss = vi.fn();

      render(
        <AlertPanel
          alerts={alerts}
          loading={false}
          error={null}
          onRefresh={vi.fn()}
          onExecutePlaybook={mockExecutePlaybookChain}
          onDismissAlert={onDismiss}
        />
      );

      expect(screen.getByTestId("dismiss-alert-btn-alert-1")).toBeInTheDocument();
    });

    it("should call onDismissAlert when dismiss button is clicked", () => {
      const alerts = [createMockAlert({ alert_id: "alert-1" })];
      const onDismiss = vi.fn();

      render(
        <AlertPanel
          alerts={alerts}
          loading={false}
          error={null}
          onRefresh={vi.fn()}
          onExecutePlaybook={mockExecutePlaybookChain}
          onDismissAlert={onDismiss}
        />
      );

      fireEvent.click(screen.getByTestId("dismiss-alert-btn-alert-1"));
      expect(onDismiss).toHaveBeenCalledWith("alert-1");
    });
  });
});
