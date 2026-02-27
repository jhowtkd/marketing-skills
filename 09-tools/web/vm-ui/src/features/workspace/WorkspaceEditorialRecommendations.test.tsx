import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { useWorkspace, type EditorialRecommendation } from "./useWorkspace";

// Mock fetchJson e postJson
const mockFetchJson = vi.fn();
const mockPostJson = vi.fn();

vi.mock("../../api/client", () => ({
  fetchJson: (...args: any[]) => mockFetchJson(...args),
  postJson: (...args: any[]) => mockPostJson(...args),
}));

describe("Workspace Editorial Recommendations", () => {
  beforeEach(() => {
    mockFetchJson.mockClear();
    mockPostJson.mockClear();
  });

  it("fetches recommendations on mount when thread is active", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/recommendations")) {
        return Promise.resolve({
          thread_id: "t-123",
          recommendations: [
            {
              severity: "warning",
              reason: "baseline_none_rate_high",
              action_id: "create_objective_golden",
              title: "Criar Golden de Objetivo",
              description: "50% das resoluções estão sem referência",
            },
          ],
          generated_at: "2026-02-27T15:00:00Z",
        });
      }
      // Default mocks for other endpoints
      if (url.includes("/workflow-profiles")) return Promise.resolve({ profiles: [] });
      if (url.includes("/timeline")) return Promise.resolve({ items: [] });
      if (url.includes("/editorial-decisions")) return Promise.resolve({ global: null, objective: [] });
      if (url.includes("/insights")) return Promise.resolve({ totals: {}, policy: {}, baseline: {}, recency: {} });
      return Promise.resolve({});
    });

    const TestComponent = () => {
      const { recommendations, refreshRecommendations } = useWorkspace("t-123", null);
      return (
        <div>
          <button onClick={refreshRecommendations}>Refresh</button>
          {recommendations?.recommendations.map((r: EditorialRecommendation) => (
            <div key={r.action_id} data-testid="recommendation">
              <span data-testid="title">{r.title}</span>
              <span data-testid="severity">{r.severity}</span>
            </div>
          ))}
        </div>
      );
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(screen.getByTestId("title").textContent).toBe("Criar Golden de Objetivo");
    });
    expect(screen.getByTestId("severity").textContent).toBe("warning");
  });

  it("displays empty state when no recommendations", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/recommendations")) {
        return Promise.resolve({
          thread_id: "t-123",
          recommendations: [],
          generated_at: "2026-02-27T15:00:00Z",
        });
      }
      // Default mocks
      if (url.includes("/workflow-profiles")) return Promise.resolve({ profiles: [] });
      if (url.includes("/timeline")) return Promise.resolve({ items: [] });
      if (url.includes("/editorial-decisions")) return Promise.resolve({ global: null, objective: [] });
      if (url.includes("/insights")) return Promise.resolve({ totals: {}, policy: {}, baseline: {}, recency: {} });
      return Promise.resolve({});
    });

    const TestComponent = () => {
      const { recommendations } = useWorkspace("t-123", null);
      return (
        <div>
          {recommendations?.recommendations.length === 0 ? (
            <span data-testid="empty">Nenhuma ação recomendada</span>
          ) : null}
        </div>
      );
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(screen.getByTestId("empty")).toBeInTheDocument();
    });
  });

  it("calls playbook execute when action button is clicked", async () => {
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/recommendations")) {
        return Promise.resolve({
          thread_id: "t-123",
          recommendations: [
            {
              severity: "critical",
              reason: "policy_denials_increasing",
              action_id: "open_review_task",
              title: "Revisar Policy",
              description: "Muitas tentativas bloqueadas",
            },
          ],
          generated_at: "2026-02-27T15:00:00Z",
        });
      }
      if (url.includes("/playbook/execute")) {
        return Promise.resolve({
          status: "success",
          executed_action: "open_review_task",
          created_entities: [{ entity_type: "review_task", entity_id: "r-123" }],
        });
      }
      // Default mocks
      if (url.includes("/workflow-profiles")) return Promise.resolve({ profiles: [] });
      if (url.includes("/timeline")) return Promise.resolve({ items: [] });
      if (url.includes("/editorial-decisions")) return Promise.resolve({ global: null, objective: [] });
      if (url.includes("/insights")) return Promise.resolve({ totals: {}, policy: {}, baseline: {}, recency: {} });
      return Promise.resolve({});
    });

    mockPostJson.mockResolvedValue({
      status: "success",
      executed_action: "open_review_task",
      created_entities: [{ entity_type: "review_task", entity_id: "r-123" }],
    });

    const TestComponent = () => {
      const { recommendations, executePlaybookAction } = useWorkspace("t-123", "run-456");
      return (
        <div>
          {recommendations?.recommendations.map((r: EditorialRecommendation) => (
            <button
              key={r.action_id}
              data-testid="execute-btn"
              onClick={() => executePlaybookAction?.(r.action_id, "run-456")}
            >
              Executar
            </button>
          ))}
        </div>
      );
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(screen.getByTestId("execute-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("execute-btn"));

    await waitFor(() => {
      expect(mockPostJson).toHaveBeenCalled();
    });
    
    const calls = mockPostJson.mock.calls;
    expect(calls.length).toBeGreaterThan(0);
    expect(calls[0][0]).toContain("/playbook/execute");
    expect(calls[0][1]).toMatchObject({
      action_id: "open_review_task",
      run_id: "run-456",
    });
  });
});
