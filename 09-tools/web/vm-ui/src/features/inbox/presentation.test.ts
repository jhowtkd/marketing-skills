import { describe, expect, it } from "vitest";
import { splitInboxByStatus } from "./presentation";

describe("splitInboxByStatus", () => {
  it("moves completed approvals/tasks to history", () => {
    const result = splitInboxByStatus({
      tasks: [{ task_id: "t1", status: "completed", assigned_to: "", details: {} }],
      approvals: [{ approval_id: "a1", status: "pending", reason: "", required_role: "" }],
    });
    expect(result.pendingApprovals).toHaveLength(1);
    expect(result.historyTasks).toHaveLength(1);
  });
});
