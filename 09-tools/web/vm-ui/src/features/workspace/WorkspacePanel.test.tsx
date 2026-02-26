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

function buildWorkspaceState(overrides: Record<string, unknown> = {}) {
  return {
    profiles: [{ mode: "content_calendar", description: "Calendar" }],
    runs: [
      {
        run_id: "run-1",
        status: "completed",
        requested_mode: "content_calendar",
        request_text: "Lancamento 2026",
        created_at: "2026-02-26T12:00:00Z",
      },
    ],
    runDetail: { status: "completed" },
    timeline: [],
    primaryArtifact: { stageDir: "final", artifactPath: "deliverable.md", content: "# Entregavel" },
    loadingPrimaryArtifact: false,
    startRun: vi.fn(),
    resumeRun: vi.fn(),
    refreshRuns: vi.fn(),
    refreshTimeline: vi.fn(),
    refreshPrimaryArtifact: vi.fn(),
    ...overrides,
  };
}

describe("WorkspacePanel", () => {
  it("shows a strong empty state before a job is selected", () => {
    mockUseWorkspace.mockReturnValue(buildWorkspaceState({ runs: [], runDetail: null, primaryArtifact: null }));

    render(<WorkspacePanel activeThreadId={null} activeRunId={null} onSelectRun={() => {}} devMode={false} />);

    expect(screen.getAllByText("Escolha um job para abrir o canvas editorial.").length).toBeGreaterThan(0);
  });

  it("shows a human loading state while the primary deliverable is loading", () => {
    mockUseWorkspace.mockReturnValue(
      buildWorkspaceState({
        loadingPrimaryArtifact: true,
        primaryArtifact: null,
      })
    );

    render(
      <WorkspacePanel activeThreadId="t1" activeRunId="run-1" onSelectRun={() => {}} devMode={false} />
    );

    expect(screen.getByText("Preparando o preview da versao ativa...")).toBeInTheDocument();
  });

  it("prioritizes the active deliverable", () => {
    mockUseWorkspace.mockReturnValue(buildWorkspaceState());

    render(
      <WorkspacePanel activeThreadId="t1" activeRunId="run-1" onSelectRun={() => {}} devMode={false} />
    );

    expect(screen.getByRole("heading", { name: "Versao ativa" })).toBeInTheDocument();
    expect(screen.getAllByText("Objetivo do pedido").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Gerar nova versao" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Baixar .md" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Regenerar" })).toBeInTheDocument();
  });

  it("guides the user when no version is active yet", () => {
    mockUseWorkspace.mockReturnValue(
      buildWorkspaceState({
        runs: [],
        runDetail: null,
        primaryArtifact: null,
      })
    );

    render(<WorkspacePanel activeThreadId="t1" activeRunId={null} onSelectRun={() => {}} devMode={false} />);

    expect(screen.getAllByText("Ainda nao existe uma versao ativa para este job.").length).toBeGreaterThan(0);
  });
});
