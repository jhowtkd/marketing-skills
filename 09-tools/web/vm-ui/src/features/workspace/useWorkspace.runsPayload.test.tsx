import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

// Mock fetchJson before importing useWorkspace
const mockFetchJson = vi.fn();

vi.mock("../../api/client", () => ({
  fetchJson: (...args: unknown[]) => mockFetchJson(...args),
  postJson: vi.fn(),
}));

import { useWorkspace } from "./useWorkspace";

describe("useWorkspace runs payload compatibility", () => {
  beforeEach(() => {
    mockFetchJson.mockReset();
    // Default mock for profiles endpoint
    mockFetchJson.mockImplementation((url: string) => {
      if (url === "/api/v2/workflow-profiles") {
        return Promise.resolve({ profiles: [] });
      }
      return Promise.resolve({});
    });
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it("should handle API response with 'items' key instead of 'runs'", async () => {
    // Mock API returning 'items' instead of 'runs'
    mockFetchJson.mockImplementation((url: string) => {
      if (url === "/api/v2/workflow-profiles") {
        return Promise.resolve({ profiles: [] });
      }
      if (url.includes("/workflow-runs")) {
        // Return 'items' instead of 'runs' - simulates legacy or alternate API shape
        return Promise.resolve({
          items: [
            {
              run_id: "run-items-1",
              status: "completed",
              requested_mode: "content_calendar",
              request_text: "Test with items key",
              created_at: "2026-02-27T12:00:00Z",
            },
          ],
        });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ items: [] });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("thread-1", null));

    // Wait for runs to be populated from 'items' key
    await waitFor(() => {
      expect(result.current.runs.length).toBe(1);
    });

    expect(result.current.runs[0].run_id).toBe("run-items-1");
    // effectiveActiveRunId should auto-select the first run
    expect(result.current.effectiveActiveRunId).toBe("run-items-1");
  });

  it("should handle API response with 'runs' key (standard)", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url === "/api/v2/workflow-profiles") {
        return Promise.resolve({ profiles: [] });
      }
      if (url.includes("/workflow-runs")) {
        return Promise.resolve({
          runs: [
            {
              run_id: "run-standard-1",
              status: "completed",
              requested_mode: "plan_90d",
              request_text: "Test with runs key",
              created_at: "2026-02-27T12:00:00Z",
            },
          ],
        });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ items: [] });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("thread-1", null));

    await waitFor(() => {
      expect(result.current.runs.length).toBe(1);
    });

    expect(result.current.runs[0].run_id).toBe("run-standard-1");
    expect(result.current.effectiveActiveRunId).toBe("run-standard-1");
  });

  it("should fallback to empty array when neither 'runs' nor 'items' present", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url === "/api/v2/workflow-profiles") {
        return Promise.resolve({ profiles: [] });
      }
      if (url.includes("/workflow-runs")) {
        // Return empty object - no runs or items key
        return Promise.resolve({});
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ items: [] });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("thread-1", null));

    await waitFor(() => {
      expect(result.current.loadingRuns).toBe(false);
    });

    expect(result.current.runs).toEqual([]);
    expect(result.current.effectiveActiveRunId).toBeNull();
  });

  it("should prefer 'runs' over 'items' when both present", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url === "/api/v2/workflow-profiles") {
        return Promise.resolve({ profiles: [] });
      }
      if (url.includes("/workflow-runs")) {
        // Return both keys - should prefer 'runs'
        return Promise.resolve({
          runs: [
            {
              run_id: "run-preferred",
              status: "completed",
              requested_mode: "plan_90d",
              request_text: "From runs key",
              created_at: "2026-02-27T12:00:00Z",
            },
          ],
          items: [
            {
              run_id: "run-ignored",
              status: "completed",
              requested_mode: "content_calendar",
              request_text: "From items key",
              created_at: "2026-02-27T10:00:00Z",
            },
          ],
        });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ items: [] });
      }
      return Promise.resolve({});
    });

    const { result } = renderHook(() => useWorkspace("thread-1", null));

    await waitFor(() => {
      expect(result.current.runs.length).toBe(1);
    });

    // Should use 'runs' key, not 'items'
    expect(result.current.runs[0].run_id).toBe("run-preferred");
  });
});
