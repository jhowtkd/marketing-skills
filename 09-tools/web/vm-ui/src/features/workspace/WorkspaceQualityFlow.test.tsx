import { fireEvent, render, screen } from "@testing-library/react";
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
        run_id: "run-2",
        status: "completed",
        requested_mode: "content_calendar",
        request_text: "Plano v2",
        created_at: "2026-02-27T12:00:00Z",
      },
      {
        run_id: "run-1",
        status: "completed",
        requested_mode: "content_calendar",
        request_text: "Plano v1",
        created_at: "2026-02-26T12:00:00Z",
      },
    ],
    effectiveActiveRunId: "run-2",
    runDetail: { status: "completed" },
    timeline: [],
    primaryArtifact: {
      stageDir: "final",
      artifactPath: "deliverable-v2.md",
      content: "# Plano\n## CTA\nComprar agora\n- passo novo",
    },
    artifactsByRun: {
      "run-1": {
        stageDir: "final",
        artifactPath: "deliverable-v1.md",
        content: "# Plano\n## CTA\nAssinar agora",
      },
      "run-2": {
        stageDir: "final",
        artifactPath: "deliverable-v2.md",
        content: "# Plano\n## CTA\nComprar agora\n- passo novo",
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
    ...overrides,
  };
}

describe("Workspace quality flow", () => {
  it("renders scorecard for active version and compares with previous version", () => {
    mockUseWorkspace.mockReturnValue(buildWorkspaceState());

    render(<WorkspacePanel activeThreadId="t1" activeRunId="run-2" onSelectRun={() => {}} devMode={false} />);

    expect(screen.getByText("Score geral")).toBeInTheDocument();
    expect(screen.getByText("Comparando com a versao anterior")).toBeInTheDocument();
    expect(screen.getByText("Diff entre versoes")).toBeInTheDocument();
  });

  it("opens guided regenerate modal", () => {
    mockUseWorkspace.mockReturnValue(buildWorkspaceState());

    render(<WorkspacePanel activeThreadId="t1" activeRunId="run-2" onSelectRun={() => {}} devMode={false} />);

    fireEvent.click(screen.getByRole("button", { name: "Regenerar guiado" }));

    expect(screen.getByText("Regeneracao guiada")).toBeInTheDocument();
  });
});
