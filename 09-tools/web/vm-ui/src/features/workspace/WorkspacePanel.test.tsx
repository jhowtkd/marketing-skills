import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import WorkspacePanel from "./WorkspacePanel";

vi.mock("./useWorkspace", () => ({
  useWorkspace: () => ({
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
  }),
}));

vi.mock("./viewState", () => ({
  readWorkspaceView: () => "studio",
  writeWorkspaceView: vi.fn(),
}));

describe("WorkspacePanel", () => {
  it("prioritizes the active deliverable", () => {
    render(
      <WorkspacePanel activeThreadId="t1" activeRunId="run-1" onSelectRun={() => {}} devMode={false} />
    );

    expect(screen.getByRole("heading", { name: "Versao ativa" })).toBeInTheDocument();
    expect(screen.getAllByText("Objetivo do pedido").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Gerar nova versao" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Baixar .md" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Regenerar" })).toBeInTheDocument();
  });
});
