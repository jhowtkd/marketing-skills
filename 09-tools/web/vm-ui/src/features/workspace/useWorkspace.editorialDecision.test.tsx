import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useWorkspace } from "./useWorkspace";

// Mock fetchJson e postJson
const mockFetchJson = vi.fn();
const mockPostJson = vi.fn();

vi.mock("../../api/client", () => ({
  fetchJson: (...args: any[]) => mockFetchJson(...args),
  postJson: (...args: any[]) => mockPostJson(...args),
}));

describe("useWorkspace - Editorial Decisions", () => {
  beforeEach(() => {
    mockFetchJson.mockClear();
    mockPostJson.mockClear();
  });

  it("loads editorial decisions and resolved baseline for effective active run", async () => {
    // Setup mocks
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/workflow-profiles")) {
        return Promise.resolve({ profiles: [] });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ items: [] });
      }
      if (url.includes("/editorial-decisions")) {
        return Promise.resolve({
          global: { run_id: "run-1", justification: "best overall", updated_at: "2026-01-01T00:00:00Z" },
          objective: [],
        });
      }
      if (url.includes("/baseline")) {
        return Promise.resolve({
          baseline_run_id: "run-1",
          source: "objective_golden",
          objective_key: "campanha-lancamento-abc123",
        });
      }
      // Default: runs list
      return Promise.resolve({
        runs: [
          { run_id: "run-2", status: "completed", requested_mode: "content_calendar", request_text: "Test", objective_key: "campanha-lancamento-abc123" },
          { run_id: "run-1", status: "completed", requested_mode: "content_calendar", request_text: "Test 1", objective_key: "campanha-lancamento-abc123" },
        ],
      });
    });

    const { result } = renderHook(() => useWorkspace("thread-1", "run-2"));

    // Wait for editorial decisions to be loaded
    await waitFor(() => {
      expect(result.current.editorialDecisions).toBeDefined();
    }, { timeout: 3000 });

    expect(result.current.editorialDecisions?.global?.run_id).toBe("run-1");
  });

  it("falls back to local baseline when API fails", async () => {
    // Setup mocks - baseline endpoint fails
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/workflow-profiles")) {
        return Promise.resolve({ profiles: [] });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ items: [] });
      }
      if (url.includes("/editorial-decisions")) {
        return Promise.reject(new Error("API Error"));
      }
      if (url.includes("/baseline")) {
        return Promise.reject(new Error("API Error"));
      }
      // Default: runs list
      return Promise.resolve({
        runs: [
          { run_id: "run-2", status: "completed", requested_mode: "content_calendar", request_text: "Test", objective_key: "campanha-lancamento-abc123" },
          { run_id: "run-1", status: "completed", requested_mode: "content_calendar", request_text: "Test 1", objective_key: "campanha-lancamento-abc123" },
        ],
      });
    });

    const { result } = renderHook(() => useWorkspace("thread-1", "run-2"));

    // Wait for initial load
    await waitFor(() => {
      expect(result.current.runs.length).toBeGreaterThan(0);
    }, { timeout: 3000 });

    // Fallback local deve estar disponível (anterior por posição)
    expect(result.current.localBaseline).toBeDefined();
    expect(result.current.localBaseline?.run_id).toBe("run-1");
  });

  it("exposes markGoldenDecision method", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/workflow-profiles")) {
        return Promise.resolve({ profiles: [] });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ items: [] });
      }
      if (url.includes("/editorial-decisions")) {
        return Promise.resolve({ global: null, objective: [] });
      }
      return Promise.resolve({ runs: [] });
    });

    mockPostJson.mockResolvedValue({
      event_id: "evt-golden-1",
      thread_id: "thread-1",
      run_id: "run-1",
      scope: "global",
    });

    const { result } = renderHook(() => useWorkspace("thread-1", "run-1"));

    // Wait for initial load
    await waitFor(() => {
      expect(result.current.markGoldenDecision).toBeDefined();
    }, { timeout: 3000 });

    // Call markGoldenDecision
    await result.current.markGoldenDecision({
      runId: "run-1",
      scope: "global",
      justification: "melhor versao",
    });

    expect(mockPostJson).toHaveBeenCalledWith(
      expect.stringContaining("/editorial-decisions/golden"),
      expect.objectContaining({
        run_id: "run-1",
        scope: "global",
        justification: "melhor versao",
      }),
      expect.any(String)
    );
  });
});
