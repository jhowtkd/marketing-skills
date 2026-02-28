import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useWorkspace } from "./useWorkspace";
import * as client from "../../api/client";

describe("useWorkspace - first-run recommendation", () => {
  const mockFetchJson = vi.spyOn(client, "fetchJson");

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads first-run recommendation with confidence and reason codes", async () => {
    const mockRecommendation = {
      thread_id: "t1",
      scope: "objective",
      recommendations: [
        {
          profile: "engagement",
          mode: "fast",
          score: 0.85,
          confidence: 0.75,
          reason_codes: ["high_success_rate", "quality"],
        },
        {
          profile: "conversion",
          mode: "quality",
          score: 0.72,
          confidence: 0.65,
          reason_codes: ["success_rate"],
        },
      ],
    };

    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/first-run-recommendation")) {
        return Promise.resolve(mockRecommendation);
      }
      if (url.includes("/workflow-runs")) {
        return Promise.resolve({ runs: [] });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ events: [] });
      }
      if (url.includes("/editorial-decisions")) {
        return Promise.resolve({ global: null, objective: [] });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("t1", null));

    // Wait for the recommendation to be loaded
    await waitFor(() => {
      expect(result.current.firstRunRecommendation).not.toBeNull();
    });

    expect(result.current.firstRunRecommendation?.recommendations).toHaveLength(2);
    expect(result.current.firstRunRecommendation?.recommendations[0].profile).toBe("engagement");
    expect(result.current.firstRunRecommendation?.recommendations[0].confidence).toBe(0.75);
    expect(result.current.firstRunRecommendation?.recommendations[0].reason_codes).toContain("high_success_rate");
    expect(result.current.firstRunRecommendation?.scope).toBe("objective");
  });

  it("falls back safely when recommendation api fails", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/first-run-recommendation")) {
        return Promise.reject(new Error("API Error"));
      }
      if (url.includes("/workflow-runs")) {
        return Promise.resolve({ runs: [] });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ events: [] });
      }
      if (url.includes("/editorial-decisions")) {
        return Promise.resolve({ global: null, objective: [] });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("t1", null));

    // Wait for loading to complete
    await waitFor(() => {
      expect(result.current.loadingFirstRunRecommendation).toBe(false);
    });

    // Should have null recommendation but not crash
    expect(result.current.firstRunRecommendation).toBeNull();
    expect(result.current.refreshFirstRunRecommendation).toBeDefined();
  });

  it("allows manual refresh of first-run recommendation", async () => {
    const mockRecommendation = {
      thread_id: "t1",
      scope: "objective",
      recommendations: [
        {
          profile: "engagement",
          mode: "fast",
          score: 0.85,
          confidence: 0.75,
          reason_codes: ["high_success_rate"],
        },
      ],
    };

    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/first-run-recommendation")) {
        return Promise.resolve(mockRecommendation);
      }
      if (url.includes("/workflow-runs")) {
        return Promise.resolve({ runs: [] });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ events: [] });
      }
      if (url.includes("/editorial-decisions")) {
        return Promise.resolve({ global: null, objective: [] });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("t1", null));

    await waitFor(() => {
      expect(result.current.firstRunRecommendation).not.toBeNull();
    });

    // Clear and call refresh
    vi.clearAllMocks();
    await result.current.refreshFirstRunRecommendation();

    // Should have fetched again
    expect(mockFetchJson).toHaveBeenCalledWith(
      "/api/v2/threads/t1/first-run-recommendation"
    );
  });

  it("exposes outcomes data for the thread", async () => {
    const mockOutcomes = {
      thread_id: "t1",
      aggregates: [
        {
          profile: "engagement",
          mode: "fast",
          total_runs: 10,
          success_24h_count: 8,
          success_rate: 0.8,
          avg_quality_score: 0.85,
          avg_duration_ms: 4000,
        },
      ],
    };

    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/first-run-outcomes")) {
        return Promise.resolve(mockOutcomes);
      }
      if (url.includes("/workflow-runs")) {
        return Promise.resolve({ runs: [] });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ events: [] });
      }
      if (url.includes("/editorial-decisions")) {
        return Promise.resolve({ global: null, objective: [] });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("t1", null));

    await waitFor(() => {
      expect(result.current.firstRunOutcomes).not.toBeNull();
    });

    expect(result.current.firstRunOutcomes?.aggregates).toHaveLength(1);
    expect(result.current.firstRunOutcomes?.aggregates[0].total_runs).toBe(10);
    expect(result.current.firstRunOutcomes?.aggregates[0].success_rate).toBe(0.8);
  });
});
