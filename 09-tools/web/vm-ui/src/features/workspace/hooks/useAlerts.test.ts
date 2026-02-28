import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useAlerts } from "./useAlerts";

const mockFetchJson = vi.fn();
const mockPostJson = vi.fn();

vi.mock("../../../api/client", () => ({
  fetchJson: (...args: any[]) => mockFetchJson(...args),
  postJson: (...args: any[]) => mockPostJson(...args),
}));

describe("useAlerts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Initial state", () => {
    it("should have initial loading state as false", () => {
      const { result } = renderHook(() => useAlerts(null));
      expect(result.current.loading).toBe(false);
    });

    it("should have initial alerts as empty array", () => {
      const { result } = renderHook(() => useAlerts(null));
      expect(result.current.alerts).toEqual([]);
    });

    it("should have initial error as null", () => {
      const { result } = renderHook(() => useAlerts(null));
      expect(result.current.error).toBeNull();
    });
  });

  describe("Fetching alerts", () => {
    it("should fetch alerts when threadId is provided", async () => {
      const mockAlerts = [
        {
          alert_id: "alert-1",
          severity: "critical",
          cause: "API_FAILURE",
          recommendation: "Retry the failed request",
          created_at: "2026-02-27T10:00:00Z",
          updated_at: "2026-02-27T10:00:00Z",
        },
      ];

      mockFetchJson.mockResolvedValue({ alerts: mockAlerts });

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch on mount
      await waitFor(() => {
        expect(result.current.alerts).toEqual(mockAlerts);
      });

      expect(mockFetchJson).toHaveBeenCalledWith("/api/v2/threads/thread-1/alerts");
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should handle multiple alerts with different severities", async () => {
      const mockAlerts = [
        {
          alert_id: "alert-1",
          severity: "critical",
          cause: "SYSTEM_ERROR",
          recommendation: "Contact support",
          created_at: "2026-02-27T10:00:00Z",
          updated_at: "2026-02-27T10:00:00Z",
        },
        {
          alert_id: "alert-2",
          severity: "warning",
          cause: "PERFORMANCE_DEGRADATION",
          recommendation: "Monitor system",
          created_at: "2026-02-27T09:00:00Z",
          updated_at: "2026-02-27T09:00:00Z",
        },
        {
          alert_id: "alert-3",
          severity: "info",
          cause: "CONFIGURATION_UPDATED",
          recommendation: "No action needed",
          created_at: "2026-02-27T08:00:00Z",
          updated_at: "2026-02-27T08:00:00Z",
        },
      ];

      mockFetchJson.mockResolvedValue({ alerts: mockAlerts });

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch on mount
      await waitFor(() => {
        expect(result.current.alerts).toHaveLength(3);
      });

      expect(result.current.alerts[0].severity).toBe("critical");
      expect(result.current.alerts[1].severity).toBe("warning");
      expect(result.current.alerts[2].severity).toBe("info");
    });

    it("should set loading state while fetching", async () => {
      mockFetchJson.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ alerts: [] }), 100))
      );

      const { result } = renderHook(() => useAlerts("thread-1"));

      act(() => {
        result.current.fetchAlerts();
      });

      expect(result.current.loading).toBe(true);

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
    });

    it("should not fetch when threadId is null", async () => {
      const { result } = renderHook(() => useAlerts(null));

      await act(async () => {
        await result.current.fetchAlerts();
      });

      expect(mockFetchJson).not.toHaveBeenCalled();
      expect(result.current.alerts).toEqual([]);
    });

    it("should clear alerts when threadId changes to null", async () => {
      mockFetchJson.mockResolvedValue({
        alerts: [{ alert_id: "alert-1", severity: "critical", cause: "ERROR", recommendation: "Fix" }],
      });

      const { result, rerender } = renderHook(({ threadId }) => useAlerts(threadId), {
        initialProps: { threadId: "thread-1" as string | null },
      });

      // Wait for auto-fetch on mount
      await waitFor(() => {
        expect(result.current.alerts).toHaveLength(1);
      });

      rerender({ threadId: null });

      // Wait for effect to clear alerts
      await waitFor(() => {
        expect(result.current.alerts).toEqual([]);
      });
    });
  });

  describe("Error handling", () => {
    it("should set error state when API fails", async () => {
      mockFetchJson.mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch to fail
      await waitFor(() => {
        expect(result.current.error).toBe("Network error");
      });

      expect(result.current.loading).toBe(false);
      expect(result.current.alerts).toEqual([]);
    });

    it("should set error message from API response detail", async () => {
      // Simulate the error handling in fetchJson
      mockFetchJson.mockImplementation(async () => {
        const error = new Error("Invalid thread ID");
        throw error;
      });

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch to fail
      await waitFor(() => {
        expect(result.current.error).toBe("Invalid thread ID");
      });
    });

    it("should clear error state on successful fetch after error", async () => {
      mockFetchJson.mockRejectedValueOnce(new Error("First error"));

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch to fail
      await waitFor(() => {
        expect(result.current.error).toBe("First error");
      });

      // Reset mock for successful refresh
      mockFetchJson.mockResolvedValue({ alerts: [] });

      await act(async () => {
        await result.current.refreshAlerts();
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe("Refresh functionality", () => {
    it("should allow manual refresh of alerts", async () => {
      const initialAlerts = [{ alert_id: "alert-1", severity: "warning", cause: "TEST", recommendation: "Test" }];
      const updatedAlerts = [
        { alert_id: "alert-1", severity: "warning", cause: "TEST", recommendation: "Test" },
        { alert_id: "alert-2", severity: "critical", cause: "NEW_ERROR", recommendation: "Fix now" },
      ];

      // First call (auto-fetch), second call (refresh)
      mockFetchJson
        .mockResolvedValueOnce({ alerts: initialAlerts })
        .mockResolvedValueOnce({ alerts: updatedAlerts });

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch on mount
      await waitFor(() => {
        expect(result.current.alerts).toHaveLength(1);
      });

      // Mock next call for refresh
      mockFetchJson.mockResolvedValue({ alerts: updatedAlerts });

      await act(async () => {
        await result.current.refreshAlerts();
      });

      expect(result.current.alerts).toHaveLength(2);
      expect(mockFetchJson).toHaveBeenCalledTimes(2);
    });
  });

  describe("Execute playbook chain", () => {
    it("should execute playbook chain via POST API", async () => {
      const mockResponse = {
        status: "success",
        executed: ["step-1", "step-2"],
        skipped: ["step-3"],
        errors: [],
        execution_id: "exec-123",
      };

      mockPostJson.mockResolvedValueOnce(mockResponse);

      const { result } = renderHook(() => useAlerts("thread-1"));

      const executionResult = await act(async () => {
        return await result.current.executePlaybookChain("chain-1");
      });

      expect(mockPostJson).toHaveBeenCalledWith(
        "/api/v2/threads/thread-1/playbooks/execute",
        { chain_id: "chain-1" },
        "playbook"
      );
      expect(executionResult).toEqual(mockResponse);
    });

    it("should include runId in execution payload when provided", async () => {
      mockPostJson.mockResolvedValueOnce({ status: "success", executed: [], skipped: [], errors: [] });

      const { result } = renderHook(() => useAlerts("thread-1"));

      await act(async () => {
        await result.current.executePlaybookChain("chain-1", "run-123");
      });

      expect(mockPostJson).toHaveBeenCalledWith(
        "/api/v2/threads/thread-1/playbooks/execute",
        { chain_id: "chain-1", run_id: "run-123" },
        "playbook"
      );
    });

    it("should throw error when threadId is null", async () => {
      const { result } = renderHook(() => useAlerts(null));

      await expect(result.current.executePlaybookChain("chain-1")).rejects.toThrow("No active thread");
    });

    it("should propagate execution errors", async () => {
      mockPostJson.mockRejectedValueOnce(new Error("Execution failed"));

      const { result } = renderHook(() => useAlerts("thread-1"));

      await expect(result.current.executePlaybookChain("chain-1")).rejects.toThrow("Execution failed");
    });

    it("should track execution state during playbook execution", async () => {
      mockPostJson.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ status: "success" }), 100))
      );

      const { result } = renderHook(() => useAlerts("thread-1"));

      act(() => {
        result.current.executePlaybookChain("chain-1");
      });

      expect(result.current.executing).toBe(true);

      await waitFor(() => {
        expect(result.current.executing).toBe(false);
      });
    });
  });

  describe("Alert filtering and helpers", () => {
    it("should return critical alerts only", async () => {
      const mockAlerts = [
        { alert_id: "alert-1", severity: "critical", cause: "ERROR", recommendation: "Fix" },
        { alert_id: "alert-2", severity: "warning", cause: "WARN", recommendation: "Check" },
        { alert_id: "alert-3", severity: "critical", cause: "FAILURE", recommendation: "Repair" },
      ];

      mockFetchJson.mockResolvedValue({ alerts: mockAlerts });

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch on mount
      await waitFor(() => {
        expect(result.current.alerts).toHaveLength(3);
      });

      expect(result.current.criticalAlerts).toHaveLength(2);
      expect(result.current.criticalAlerts.every((a) => a.severity === "critical")).toBe(true);
    });

    it("should return true for hasAlerts when alerts exist", async () => {
      mockFetchJson.mockResolvedValue({
        alerts: [{ alert_id: "alert-1", severity: "info", cause: "INFO", recommendation: "Note" }],
      });

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch on mount
      await waitFor(() => {
        expect(result.current.alerts).toHaveLength(1);
      });

      expect(result.current.hasAlerts).toBe(true);
    });

    it("should return false for hasAlerts when no alerts", async () => {
      mockFetchJson.mockResolvedValue({ alerts: [] });

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch to complete
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.alerts).toEqual([]);
      expect(result.current.hasAlerts).toBe(false);
    });

    it("should count alerts by severity", async () => {
      const mockAlerts = [
        { alert_id: "1", severity: "critical", cause: "E", recommendation: "R" },
        { alert_id: "2", severity: "critical", cause: "E", recommendation: "R" },
        { alert_id: "3", severity: "warning", cause: "E", recommendation: "R" },
        { alert_id: "4", severity: "info", cause: "E", recommendation: "R" },
      ];

      mockFetchJson.mockResolvedValue({ alerts: mockAlerts });

      const { result } = renderHook(() => useAlerts("thread-1"));

      // Wait for auto-fetch on mount
      await waitFor(() => {
        expect(result.current.alerts).toHaveLength(4);
      });

      expect(result.current.alertCounts).toEqual({
        total: 4,
        critical: 2,
        warning: 1,
        info: 1,
      });
    });
  });

  describe("Auto-fetch on mount", () => {
    it("should auto-fetch alerts when threadId is provided on mount", async () => {
      mockFetchJson.mockResolvedValueOnce({ alerts: [] });

      renderHook(() => useAlerts("thread-1"));

      await waitFor(() => {
        expect(mockFetchJson).toHaveBeenCalledWith("/api/v2/threads/thread-1/alerts");
      });
    });

    it("should not auto-fetch when threadId is null", async () => {
      renderHook(() => useAlerts(null));

      // Wait a bit to ensure no fetch happens
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(mockFetchJson).not.toHaveBeenCalled();
    });
  });
});
