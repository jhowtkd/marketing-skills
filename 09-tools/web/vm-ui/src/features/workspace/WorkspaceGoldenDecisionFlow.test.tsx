import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { renderHook, waitFor as waitForHook } from "@testing-library/react";
import { useWorkspace } from "./useWorkspace";
import GoldenDecisionModal from "./GoldenDecisionModal";

// Mocks
const mockFetchJson = vi.fn();
const mockPostJson = vi.fn();

vi.mock("../../api/client", () => ({
  fetchJson: (...args: any[]) => mockFetchJson(...args),
  postJson: (...args: any[]) => mockPostJson(...args),
}));

describe("useWorkspace - Editorial Decisions Integration", () => {
  beforeEach(() => {
    mockFetchJson.mockClear();
    mockPostJson.mockClear();
    
    // Default mock responses
    mockFetchJson.mockImplementation((url: string) => {
      if (url.includes("/workflow-profiles")) {
        return Promise.resolve({ profiles: [{ mode: "content_calendar", description: "Test" }] });
      }
      if (url.includes("/timeline")) {
        return Promise.resolve({ items: [] });
      }
      if (url.includes("/editorial-decisions")) {
        return Promise.resolve({ global: null, objective: [] });
      }
      if (url.includes("/baseline")) {
        return Promise.resolve({ baseline_run_id: null, source: "none", objective_key: "" });
      }
      if (url.includes("/workflow-runs/") && !url.includes("/artifacts")) {
        return Promise.resolve({
          run_id: "run-1",
          status: "completed",
          request_text: "Campanha Lancamento",
          objective_key: "campanha-lancamento-abc123",
          stages: [],
        });
      }
      return Promise.resolve({
        runs: [
          { run_id: "run-1", status: "completed", requested_mode: "content_calendar", request_text: "Campanha Lancamento", created_at: "2026-01-01T00:00:00Z", objective_key: "campanha-lancamento-abc123" },
        ],
      });
    });
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
      return Promise.resolve({
        runs: [
          { run_id: "run-2", status: "completed", requested_mode: "content_calendar", request_text: "Test", objective_key: "campanha-lancamento-abc123" },
          { run_id: "run-1", status: "completed", requested_mode: "content_calendar", request_text: "Test 1", objective_key: "campanha-lancamento-abc123" },
        ],
      });
    });

    const { result } = renderHook(() => useWorkspace("thread-1", "run-2"));

    // Wait for editorial decisions to be loaded
    await waitForHook(() => {
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
      return Promise.resolve({
        runs: [
          { run_id: "run-2", status: "completed", requested_mode: "content_calendar", request_text: "Test", objective_key: "campanha-lancamento-abc123" },
          { run_id: "run-1", status: "completed", requested_mode: "content_calendar", request_text: "Test 1", objective_key: "campanha-lancamento-abc123" },
        ],
      });
    });

    const { result } = renderHook(() => useWorkspace("thread-1", "run-2"));

    // Wait for initial load
    await waitForHook(() => {
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
    await waitForHook(() => {
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

describe("GoldenDecisionModal", () => {
  it("blocks submit without justification", async () => {
    const onSubmit = vi.fn();
    const onClose = vi.fn();

    render(
      <GoldenDecisionModal
        isOpen={true}
        scope="global"
        onClose={onClose}
        onSubmit={onSubmit}
      />
    );

    // Botao deve estar desabilitado sem justificativa
    const submitButton = screen.getByText("Confirmar");
    expect(submitButton).toBeDisabled();

    // Digitar justificativa
    const textarea = screen.getByPlaceholderText(/Explique por que esta versao/);
    fireEvent.change(textarea, { target: { value: "Melhor clareza de CTA" } });

    // Botao deve estar habilitado
    expect(submitButton).not.toBeDisabled();
  });

  it("shows correct title for global scope", () => {
    render(
      <GoldenDecisionModal
        isOpen={true}
        scope="global"
        onClose={() => {}}
        onSubmit={() => {}}
      />
    );

    expect(screen.getByText("Definir como golden global")).toBeInTheDocument();
  });

  it("shows correct title for objective scope", () => {
    render(
      <GoldenDecisionModal
        isOpen={true}
        scope="objective"
        onClose={() => {}}
        onSubmit={() => {}}
      />
    );

    expect(screen.getByText("Definir como golden deste objetivo")).toBeInTheDocument();
  });
});
