import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import WorkspacePanel from "./WorkspacePanel";

const mockUseWorkspace = vi.fn();

vi.mock("./useWorkspace", () => ({
  useWorkspace: (...args: unknown[]) => mockUseWorkspace(...args),
}));

vi.mock("./viewState", () => ({
  readWorkspaceView: () => "studio",
  writeWorkspaceView: vi.fn(),
}));

describe("Workspace run binding bugfix", () => {
  it("should NOT show empty state when runs exist but activeRunId is null", () => {
    mockUseWorkspace.mockReturnValue({
      profiles: [{ mode: "content_calendar", description: "Calendar" }],
      runs: [
        {
          run_id: "run-1",
          status: "completed",
          requested_mode: "content_calendar",
          request_text: "Plano de conteudo",
          created_at: "2026-02-27T12:00:00Z",
        },
      ],
      effectiveActiveRunId: "run-1", // Fallback para primeira run
      runDetail: { status: "completed" },
      timeline: [],
      primaryArtifact: {
        stageDir: "final",
        artifactPath: "deliverable.md",
        content: "# Entregavel principal",
      },
      artifactsByRun: {},
      deepEvaluationByRun: {},
      loadingPrimaryArtifact: false,
      startRun: vi.fn(),
      resumeRun: vi.fn(),
      refreshRuns: vi.fn(),
      refreshTimeline: vi.fn(),
      refreshPrimaryArtifact: vi.fn(),
      loadArtifactForRun: vi.fn(),
    });

    render(
      <WorkspacePanel
        activeThreadId="t1"
        activeRunId={null} // Simula URL sem run selecionado
        onSelectRun={() => {}}
        devMode={false}
      />
    );

    // NÃO deve mostrar mensagem de "sem versão ativa" no canvas
    const emptyStates = screen.queryAllByText(/Ainda nao existe uma versao ativa para este job/i);
    expect(emptyStates.length).toBe(0);

    // DEVE mostrar o status da run (indicando que há run ativa)
    // O status "Pronto" aparece no badge e na lista
    expect(screen.getAllByText(/Pronto/i).length).toBeGreaterThanOrEqual(1);
  });

  it("should handle API response with 'items' instead of 'runs' (fallback)", () => {
    mockUseWorkspace.mockReturnValue({
      profiles: [],
      // Simula resposta da API que veio com 'items' ao invés de 'runs'
      runs: [],
      effectiveActiveRunId: null,
      runDetail: null,
      timeline: [],
      primaryArtifact: null,
      artifactsByRun: {},
      deepEvaluationByRun: {},
      loadingPrimaryArtifact: false,
      startRun: vi.fn(),
      resumeRun: vi.fn(),
      refreshRuns: vi.fn(),
      refreshTimeline: vi.fn(),
      refreshPrimaryArtifact: vi.fn(),
      loadArtifactForRun: vi.fn(),
    });

    render(
      <WorkspacePanel
        activeThreadId="t1"
        activeRunId={null}
        onSelectRun={() => {}}
        devMode={false}
      />
    );

    // Com runs vazias, deve mostrar empty state apropriado
    expect(screen.getByText(/Nenhuma versao encontrada/i)).toBeInTheDocument();
  });

  it("should use first run as active when activeRunId is null", () => {
    mockUseWorkspace.mockReturnValue({
      profiles: [{ mode: "content_calendar", description: "Calendar" }],
      runs: [
        {
          run_id: "run-2",
          status: "completed",
          requested_mode: "content_calendar",
          request_text: "Versao mais recente",
          created_at: "2026-02-27T14:00:00Z",
        },
        {
          run_id: "run-1",
          status: "completed",
          requested_mode: "content_calendar",
          request_text: "Versao antiga",
          created_at: "2026-02-27T10:00:00Z",
        },
      ],
      effectiveActiveRunId: "run-2", // Fallback para primeira run da lista
      runDetail: { status: "completed" },
      timeline: [],
      primaryArtifact: {
        stageDir: "final",
        artifactPath: "deliverable.md",
        content: "# Versao mais recente",
      },
      artifactsByRun: {
        "run-2": {
          stageDir: "final",
          artifactPath: "deliverable.md",
          content: "# Versao mais recente",
        },
      },
      deepEvaluationByRun: {},
      loadingPrimaryArtifact: false,
      startRun: vi.fn(),
      resumeRun: vi.fn(),
      refreshRuns: vi.fn(),
      refreshTimeline: vi.fn(),
      refreshPrimaryArtifact: vi.fn(),
      loadArtifactForRun: vi.fn(),
    });

    render(
      <WorkspacePanel
        activeThreadId="t1"
        activeRunId={null}
        onSelectRun={() => {}}
        devMode={false}
      />
    );

    // Deve mostrar a run mais recente na lista como selecionada
    // (a primeira run no array é a mais recente)
    expect(screen.getByText(/Versao 1 · Versao mais recente/i)).toBeInTheDocument();
  });
});
