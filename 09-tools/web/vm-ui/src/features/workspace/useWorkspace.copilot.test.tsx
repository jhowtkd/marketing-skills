import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useWorkspace } from "./useWorkspace";
import * as client from "../../api/client";

// Mock the API client
vi.mock("../../api/client", () => ({
  fetchJson: vi.fn(),
  postJson: vi.fn(),
}));

describe("useWorkspace copilot integration", () => {
  const mockFetchJson = vi.mocked(client.fetchJson);
  const mockPostJson = vi.mocked(client.postJson);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads copilot suggestions for selected phase", async () => {
    const mockSuggestion = {
      suggestion_id: "sugg-123",
      content: "Profile: engagement, Mode: creative",
      confidence: 0.85,
      reason_codes: ["high_success_rate"],
      why: "Based on historical data",
      expected_impact: { quality_delta: 10, approval_lift: 8 },
      created_at: "2026-02-28T12:00:00Z",
    };

    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/copilot/suggestions")) {
        return Promise.resolve({
          thread_id: "thread-123",
          phase: "initial",
          suggestions: [mockSuggestion],
          guardrail_applied: false,
        });
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

    const { result } = renderHook(() => useWorkspace("thread-123", null));

    // Wait for initial loading to complete
    await waitFor(() => expect(result.current.loadingCopilot).toBe(false));

    // Refresh copilot suggestions
    result.current.refreshCopilotSuggestions("initial");

    await waitFor(() =>
      expect(result.current.copilotSuggestions).toHaveLength(1)
    );

    expect(result.current.copilotPhase).toBe("initial");
    expect(result.current.copilotSuggestions[0]).toMatchObject({
      suggestion_id: "sugg-123",
      confidence: 0.85,
    });
    expect(mockFetchJson).toHaveBeenCalledWith(
      expect.stringContaining("/threads/thread-123/copilot/suggestions"),
      expect.any(Object)
    );
  });

  it("submits feedback action accepted", async () => {
    mockPostJson.mockResolvedValueOnce({
      feedback_id: "feedback-123",
      suggestion_id: "sugg-123",
      thread_id: "thread-123",
      phase: "initial",
      action: "accepted",
      created_at: "2026-02-28T12:00:00Z",
    });

    mockFetchJson.mockImplementation((url: string) => {
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

    const { result } = renderHook(() => useWorkspace("thread-123", null));

    await waitFor(() => expect(result.current.loadingCopilot).toBe(false));

    const feedback = await result.current.submitCopilotFeedback({
      suggestion_id: "sugg-123",
      phase: "initial",
      action: "accepted",
    });

    expect(feedback).toMatchObject({
      feedback_id: "feedback-123",
      action: "accepted",
    });
    expect(mockPostJson).toHaveBeenCalledWith(
      expect.stringContaining("/threads/thread-123/copilot/feedback"),
      expect.objectContaining({
        suggestion_id: "sugg-123",
        phase: "initial",
        action: "accepted",
      })
    );
  });

  it("submits feedback action edited", async () => {
    mockPostJson.mockResolvedValueOnce({
      feedback_id: "feedback-456",
      suggestion_id: "sugg-123",
      thread_id: "thread-123",
      phase: "refine",
      action: "edited",
      created_at: "2026-02-28T12:00:00Z",
    });

    mockFetchJson.mockImplementation((url: string) => {
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

    const { result } = renderHook(() => useWorkspace("thread-123", null));

    await waitFor(() => expect(result.current.loadingCopilot).toBe(false));

    const feedback = await result.current.submitCopilotFeedback({
      suggestion_id: "sugg-123",
      phase: "refine",
      action: "edited",
      edited_content: "Modified suggestion text",
    });

    expect(feedback.action).toBe("edited");
    expect(mockPostJson).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        action: "edited",
        edited_content: "Modified suggestion text",
      })
    );
  });

  it("submits feedback action ignored", async () => {
    mockPostJson.mockResolvedValueOnce({
      feedback_id: "feedback-789",
      suggestion_id: "sugg-123",
      thread_id: "thread-123",
      phase: "strategy",
      action: "ignored",
      created_at: "2026-02-28T12:00:00Z",
    });

    mockFetchJson.mockImplementation((url: string) => {
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

    const { result } = renderHook(() => useWorkspace("thread-123", null));

    await waitFor(() => expect(result.current.loadingCopilot).toBe(false));

    const feedback = await result.current.submitCopilotFeedback({
      suggestion_id: "sugg-123",
      phase: "strategy",
      action: "ignored",
    });

    expect(feedback.action).toBe("ignored");
  });

  it("handles empty suggestions (guardrail applied)", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/copilot/suggestions")) {
        return Promise.resolve({
          thread_id: "thread-123",
          phase: "initial",
          suggestions: [],
          guardrail_applied: true,
        });
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

    const { result } = renderHook(() => useWorkspace("thread-123", null));

    await waitFor(() => expect(result.current.loadingCopilot).toBe(false));

    result.current.refreshCopilotSuggestions("initial");

    await waitFor(() =>
      expect(result.current.copilotGuardrailApplied).toBe(true)
    );

    expect(result.current.copilotSuggestions).toHaveLength(0);
  });

  it("switches between phases correctly", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/copilot/suggestions?phase=initial")) {
        return Promise.resolve({
          thread_id: "thread-123",
          phase: "initial",
          suggestions: [{ suggestion_id: "sugg-1", confidence: 0.8 }],
          guardrail_applied: false,
        });
      }
      if (url.includes("/copilot/suggestions?phase=refine")) {
        return Promise.resolve({
          thread_id: "thread-123",
          phase: "refine",
          suggestions: [{ suggestion_id: "sugg-2", confidence: 0.7 }],
          guardrail_applied: false,
        });
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

    const { result } = renderHook(() => useWorkspace("thread-123", null));

    await waitFor(() => expect(result.current.loadingCopilot).toBe(false));

    // Initial phase
    result.current.refreshCopilotSuggestions("initial");
    await waitFor(() => expect(result.current.copilotPhase).toBe("initial"));

    // Switch to refine
    result.current.refreshCopilotSuggestions("refine");
    await waitFor(() => expect(result.current.copilotPhase).toBe("refine"));

    // Verify copilot endpoints were called
    const copilotCalls = mockFetchJson.mock.calls.filter(
      call => call[0] && typeof call[0] === "string" && call[0].includes("/copilot/suggestions")
    );
    expect(copilotCalls).toHaveLength(2); // 2 copilot calls
  });
});
