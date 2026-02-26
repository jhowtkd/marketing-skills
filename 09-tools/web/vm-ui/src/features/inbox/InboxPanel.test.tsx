import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import InboxPanel from "./InboxPanel";

vi.mock("./useInbox", () => ({
  useInbox: () => ({
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
  }),
}));

describe("InboxPanel", () => {
  it("prioritizes version blockers before history actions", () => {
    render(<InboxPanel activeThreadId="thread-1" activeRunId="run-1" devMode={false} />);

    expect(screen.getByRole("heading", { name: "Pendencias desta versao" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aprovar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Concluir" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Comentar" })).toBeInTheDocument();
    expect(screen.getByText("Historico recente")).toBeInTheDocument();
  });
});
