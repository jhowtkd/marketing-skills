import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useWorkspace } from "./useWorkspace";

const mockFetchJson = vi.fn();
const mockPostJson = vi.fn();

vi.mock("../../api/client", () => ({
  fetchJson: (...args: any[]) => mockFetchJson(...args),
  postJson: (...args: any[]) => mockPostJson(...args),
}));

function defaultFetchResponse(url: string) {
  if (url === "/api/v2/workflow-profiles") return { profiles: [] };
  if (url.includes("/workflow-runs") && !url.includes("/baseline")) return { runs: [] };
  if (url.endsWith("/timeline")) return { items: [] };
  if (url.endsWith("/editorial-decisions")) return { global: null, objective: [] };
  if (url.includes("/editorial-decisions/audit")) {
    return { thread_id: "thread-1", events: [], total: 0, limit: 20, offset: 0 };
  }
  if (url.includes("/editorial-decisions/insights")) {
    return {
      thread_id: "thread-1",
      totals: { marked_total: 0, by_scope: { global: 0, objective: 0 }, by_reason_code: {} },
      policy: { denied_total: 0 },
      baseline: { resolved_total: 0, by_source: { objective_golden: 0, global_golden: 0, previous: 0, none: 0 } },
      recency: { last_marked_at: null, last_actor_id: null },
    };
  }
  if (url.includes("/editorial-decisions/recommendations")) {
    return { thread_id: "thread-1", recommendations: [], generated_at: "2026-01-01T00:00:00Z" };
  }
  if (url.includes("/editorial-decisions/forecast")) {
    return {
      thread_id: "thread-1",
      risk_score: 0,
      trend: "stable",
      drivers: [],
      recommended_focus: "",
      confidence: 0,
      volatility: 0,
      calibration_notes: [],
      generated_at: "2026-01-01T00:00:00Z",
    };
  }
  if (url.includes("/events?event_types=AutoRemediationExecuted,AutoRemediationSkipped&limit=10")) {
    return { events: [] };
  }
  if (url.includes("/baseline")) {
    return { baseline_run_id: null, source: "none", objective_key: "" };
  }
  return {};
}

describe("useWorkspace - Control Center", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchJson.mockImplementation(async (url: string) => defaultFetchResponse(url));
    mockPostJson.mockResolvedValue({});
  });

  describe("Editorial SLO", () => {
    it("fetches and exposes editorial SLO for a brand", async () => {
      const mockSLO = {
        brand_id: "brand-123",
        max_baseline_none_rate: 0.5,
        max_policy_denied_rate: 0.1,
        min_confidence: 0.6,
        auto_remediation_enabled: false,
        updated_at: "2026-01-01T00:00:00Z",
      };

      mockFetchJson.mockImplementation(async (url: string) => {
        if (url === "/api/v2/brands/brand-123/editorial-slo") return mockSLO;
        return defaultFetchResponse(url);
      });

      const { result } = renderHook(() => useWorkspace("thread-1", null));
      expect(result.current.editorialSLO).toBeNull();

      await act(async () => {
        await result.current.refreshEditorialSLO("brand-123");
      });

      expect(result.current.editorialSLO).toEqual(mockSLO);
      expect(mockFetchJson).toHaveBeenCalledWith("/api/v2/brands/brand-123/editorial-slo");
    });

    it("updates editorial SLO via API", async () => {
      const mockSLO = {
        brand_id: "brand-123",
        max_baseline_none_rate: 0.3,
        max_policy_denied_rate: 0.05,
        min_confidence: 0.7,
        auto_remediation_enabled: true,
        updated_at: "2026-01-01T00:00:00Z",
      };

      mockPostJson.mockResolvedValueOnce(mockSLO);

      const { result } = renderHook(() => useWorkspace("thread-1", null));

      const updated = await act(async () => {
        return await result.current.updateEditorialSLO("brand-123", {
          auto_remediation_enabled: true,
          max_baseline_none_rate: 0.3,
        });
      });

      expect(updated).toEqual(mockSLO);
      expect(result.current.editorialSLO).toEqual(mockSLO);
      expect(mockPostJson).toHaveBeenCalledWith(
        "/api/v2/brands/brand-123/editorial-slo",
        { auto_remediation_enabled: true, max_baseline_none_rate: 0.3 },
        "workspace"
      );
    });
  });

  describe("Editorial Drift", () => {
    it("fetches and exposes drift analysis for active thread", async () => {
      const mockDrift = {
        thread_id: "thread-1",
        drift_score: 75,
        drift_severity: "high" as const,
        drift_flags: ["baseline_none_rate_violation", "confidence_violation"],
        primary_driver: "baseline_none_rate_violation",
        recommended_actions: ["open_review_task", "prepare_guided_regeneration"],
        details: {
          baseline_none_rate: 0.6,
          policy_denied_rate: 0.05,
          avg_confidence: 0.5,
        },
        generated_at: "2026-01-01T00:00:00Z",
      };

      mockFetchJson.mockImplementation(async (url: string) => {
        if (url === "/api/v2/threads/thread-1/editorial-decisions/drift") return mockDrift;
        return defaultFetchResponse(url);
      });

      const { result } = renderHook(() => useWorkspace("thread-1", null));

      await act(async () => {
        await result.current.refreshEditorialDrift();
      });

      expect(result.current.editorialDrift).toEqual(mockDrift);
      expect(mockFetchJson).toHaveBeenCalledWith("/api/v2/threads/thread-1/editorial-decisions/drift");
    });

    it("clears drift data when no active thread", async () => {
      const { result } = renderHook(() => useWorkspace(null, null));

      await act(async () => {
        await result.current.refreshEditorialDrift();
      });

      expect(result.current.editorialDrift).toBeNull();
    });
  });

  describe("Auto-remediation", () => {
    it("triggers auto-remediation via API", async () => {
      const mockResponse = {
        status: "success",
        executed: ["open_review_task"],
        skipped: [],
        event_id: "event-123",
      };

      mockPostJson.mockResolvedValueOnce(mockResponse);
      mockFetchJson.mockImplementation(async (url: string) => {
        if (url.includes("/events?event_types=AutoRemediationExecuted,AutoRemediationSkipped&limit=10")) {
          return { events: [] };
        }
        return defaultFetchResponse(url);
      });

      const { result } = renderHook(() => useWorkspace("thread-1", null));

      const response = await act(async () => {
        return await result.current.triggerAutoRemediation();
      });

      expect(response).toEqual(mockResponse);
      expect(mockPostJson).toHaveBeenCalledWith(
        "/api/v2/threads/thread-1/editorial-decisions/auto-remediate",
        { auto_execute: true },
        "workspace"
      );
    });

    it("fetches auto-remediation history from events", async () => {
      const mockEvents = {
        events: [
          {
            event_type: "AutoRemediationExecuted",
            occurred_at: "2026-01-01T10:00:00Z",
            payload: {
              action_id: "open_review_task",
              auto_executed: true,
              reason: "Drift detected",
            },
          },
          {
            event_type: "AutoRemediationSkipped",
            occurred_at: "2026-01-01T09:00:00Z",
            payload: {
              proposed_action: "suggest_policy_review",
              auto_executed: false,
              reason: "Action requires human approval",
            },
          },
        ],
      };

      mockFetchJson.mockImplementation(async (url: string) => {
        if (url.includes("/events?event_types=AutoRemediationExecuted,AutoRemediationSkipped&limit=10")) {
          return mockEvents;
        }
        return defaultFetchResponse(url);
      });

      const { result } = renderHook(() => useWorkspace("thread-1", null));

      await act(async () => {
        await result.current.refreshAutoRemediationHistory();
      });

      await waitFor(() => {
        expect(result.current.autoRemediationHistory).toHaveLength(2);
      });
      expect(result.current.autoRemediationHistory[0].event_type).toBe("AutoRemediationExecuted");
      expect(result.current.autoRemediationHistory[1].event_type).toBe("AutoRemediationSkipped");
      expect(mockFetchJson).toHaveBeenCalledWith(
        "/api/v2/threads/thread-1/events?event_types=AutoRemediationExecuted,AutoRemediationSkipped&limit=10"
      );
    });

    it("clears history when no active thread", async () => {
      const { result } = renderHook(() => useWorkspace(null, null));

      await act(async () => {
        await result.current.refreshAutoRemediationHistory();
      });

      expect(result.current.autoRemediationHistory).toEqual([]);
    });
  });
});
