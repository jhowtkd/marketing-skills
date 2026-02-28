import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useWorkspace } from "./useWorkspace";
import type { CopilotSegmentStatus } from "./useWorkspace";

// Mock the API client
vi.mock("../../api/client", () => ({
  fetchJson: vi.fn(),
  postJson: vi.fn(),
}));

import { fetchJson, postJson } from "../../api/client";

const mockFetchJson = vi.mocked(fetchJson);
const mockPostJson = vi.mocked(postJson);

describe("useWorkspace v14 Segmented Copilot", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads copilot segment status and merged suggestion payload", async () => {
    // Mock segment status response
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/copilot/segment-status")) {
        return Promise.resolve({
          thread_id: "t-123",
          brand_id: "b1",
          segment_key: "b1:awareness",
          segment_status: "insufficient_volume",
          is_eligible: false,
          segment_runs_total: 5,
          segment_success_24h_rate: 0.0,
          segment_v1_score_avg: 0.0,
          segment_regen_rate: 0.0,
          adjustment_factor: 0.0,
          minimum_runs_threshold: 20,
          explanation: "Volume insuficiente (5/20 runs). Usando ranking global v13.",
        });
      }
      if (url.includes("/copilot/suggestions")) {
        return Promise.resolve({
          thread_id: "t-123",
          phase: "initial",
          suggestions: [],
          guardrail_applied: true,
          segment_key: "b1:awareness",
          segment_status: "insufficient_volume",
          adjustment_factor: 0.0,
          is_eligible: false,
        });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("t-123", null));

    // Wait for segment status to be loaded
    await waitFor(() => {
      expect(result.current.copilotSegmentStatus).not.toBeNull();
    });

    const status = result.current.copilotSegmentStatus as CopilotSegmentStatus;
    expect(status.segment_key).toBe("b1:awareness");
    expect(status.segment_status).toBe("insufficient_volume");
    expect(status.is_eligible).toBe(false);
    expect(status.adjustment_factor).toBe(0.0);
  });

  it("falls back cleanly when segment endpoint fails", async () => {
    // Mock segment status to fail
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/copilot/segment-status")) {
        return Promise.reject(new Error("Segment status unavailable"));
      }
      if (url.includes("/copilot/suggestions")) {
        return Promise.resolve({
          thread_id: "t-123",
          phase: "initial",
          suggestions: [],
          guardrail_applied: true,
          segment_key: "b1:awareness",
          segment_status: "insufficient_volume",
          adjustment_factor: 0.0,
          is_eligible: false,
        });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("t-123", null));

    // Even if segment status fails, suggestions should still work
    await waitFor(() => {
      expect(result.current.copilotSegmentStatus).toBeNull();
    });

    // Refresh suggestions should still work
    await result.current.refreshCopilotSuggestions("initial");

    expect(result.current.copilotSuggestions).toEqual([]);
  });

  it("exposes refreshCopilotSegmentStatus function", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/copilot/segment-status")) {
        return Promise.resolve({
          thread_id: "t-123",
          brand_id: "b1",
          segment_key: "b1:conversion",
          segment_status: "eligible",
          is_eligible: true,
          segment_runs_total: 50,
          segment_success_24h_rate: 0.75,
          segment_v1_score_avg: 82.0,
          segment_regen_rate: 0.15,
          adjustment_factor: 0.08,
          minimum_runs_threshold: 20,
          explanation: "Personalização ativa (50 runs). Confiança aumentada em 8%.",
        });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("t-123", null));

    // Manually refresh segment status
    await result.current.refreshCopilotSegmentStatus();

    await waitFor(() => {
      expect(result.current.copilotSegmentStatus).not.toBeNull();
    });

    const status = result.current.copilotSegmentStatus as CopilotSegmentStatus;
    expect(status.segment_status).toBe("eligible");
    expect(status.is_eligible).toBe(true);
    expect(status.segment_runs_total).toBe(50);
  });

  it("integrates segment status with suggestion refresh", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/copilot/segment-status")) {
        return Promise.resolve({
          thread_id: "t-123",
          brand_id: "b1",
          segment_key: "b1:awareness",
          segment_status: "frozen",
          is_eligible: false,
          segment_runs_total: 30,
          segment_success_24h_rate: 0.3,
          segment_v1_score_avg: 55.0,
          segment_regen_rate: 0.45,
          adjustment_factor: 0.0,
          minimum_runs_threshold: 20,
          explanation: "Segmento congelado devido à regressão recente.",
        });
      }
      if (url.includes("/copilot/suggestions")) {
        return Promise.resolve({
          thread_id: "t-123",
          phase: "initial",
          suggestions: [],
          guardrail_applied: true,
          segment_key: "b1:awareness",
          segment_status: "frozen",
          adjustment_factor: 0.0,
          is_eligible: false,
        });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("t-123", null));

    // Refresh both suggestions and segment status
    await result.current.refreshCopilotSuggestions("initial");
    await result.current.refreshCopilotSegmentStatus();

    await waitFor(() => {
      expect(result.current.copilotSegmentStatus?.segment_status).toBe("frozen");
    });

    expect(result.current.copilotSegmentStatus?.is_eligible).toBe(false);
  });
});
