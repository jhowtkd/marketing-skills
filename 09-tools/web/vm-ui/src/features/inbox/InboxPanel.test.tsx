import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import InboxPanel from "./InboxPanel";

const mockUseInbox = vi.fn();

vi.mock("./useInbox", () => ({
  useInbox: (...args: unknown[]) => mockUseInbox(...args),
}));

function buildInboxState(overrides: Record<string, unknown> = {}) {
  return {
    tasks: [
      { task_id: "task-1", status: "pending", assigned_to: "editor", details: {} },
      { task_id: "task-2", status: "completed", assigned_to: "editor", details: {} },
    ],
    approvals: [
      { approval_id: "approval-1", status: "pending", reason: "Validar entrega", required_role: "manager" },
      { approval_id: "approval-2", status: "approved", reason: "Ja aprovado", required_role: "manager" },
    ],
    artifactStages: [],
    artifactContents: {},
    completeTask: vi.fn(),
    commentTask: vi.fn(),
    grantApproval: vi.fn(),
    loadArtifactContent: vi.fn(),
    refreshTasks: vi.fn(),
    refreshApprovals: vi.fn(),
    refreshArtifacts: vi.fn(),
    ...overrides,
  };
}

describe("InboxPanel", () => {
  it("keeps the action rail locked until a job is selected", () => {
    mockUseInbox.mockReturnValue(buildInboxState());

    render(<InboxPanel activeThreadId={null} activeRunId={null} devMode={false} />);

    expect(screen.getByText("Escolha um job para abrir a action rail da versao.")).toBeInTheDocument();
  });

  it("explains when the selected job still has no active version", () => {
    mockUseInbox.mockReturnValue(buildInboxState({ tasks: [], approvals: [] }));

    render(<InboxPanel activeThreadId="thread-1" activeRunId={null} devMode={false} />);

    expect(screen.getByText("Gere ou selecione uma versao para ver pendencias acionaveis.")).toBeInTheDocument();
  });

  it("prioritizes version blockers before history actions", () => {
    mockUseInbox.mockReturnValue(buildInboxState());

    render(<InboxPanel activeThreadId="thread-1" activeRunId="run-1" devMode={false} />);

    expect(screen.getByRole("heading", { name: "Pendencias desta versao" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aprovar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Concluir" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Comentar" })).toBeInTheDocument();
    expect(screen.getByText("Historico recente")).toBeInTheDocument();
  });
});
