import { describe, expect, it } from "vitest";
import { mapTasksResponse, mapApprovalsResponse } from "./adapters";

describe("inbox adapters", () => {
  it("maps tasks from items", () => {
    const tasks = mapTasksResponse({ items: [{ task_id: "t1", status: "pending", title: "Revisar" }] });
    expect(tasks[0].task_id).toBe("t1");
  });

  it("maps approvals from items", () => {
    const approvals = mapApprovalsResponse({ items: [{ approval_id: "a1", status: "pending", reason: "gate" }] });
    expect(approvals[0].approval_id).toBe("a1");
  });
});
