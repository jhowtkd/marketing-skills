import { Task, Approval } from "./adapters";

export type InboxSplit = {
  pendingTasks: Task[];
  pendingApprovals: Approval[];
  historyTasks: Task[];
  historyApprovals: Approval[];
};

export function splitInboxByStatus(input: { tasks: Task[]; approvals: Approval[] }): InboxSplit {
  const pendingTasks = input.tasks.filter((t) => t.status !== "completed");
  const historyTasks = input.tasks.filter((t) => t.status === "completed");
  const pendingApprovals = input.approvals.filter((a) => a.status === "pending");
  const historyApprovals = input.approvals.filter((a) => a.status !== "pending");
  return { pendingTasks, pendingApprovals, historyTasks, historyApprovals };
}
