export type Task = {
  task_id: string;
  status: string;
  assigned_to: string;
  details: unknown;
};

export type Approval = {
  approval_id: string;
  status: string;
  reason: string;
  required_role: string;
};

export function mapTasksResponse(input: unknown): Task[] {
  const items = Array.isArray((input as any)?.items) ? (input as any).items : [];
  return items.map((item: any) => ({
    task_id: String(item.task_id ?? ""),
    status: String(item.status ?? "pending"),
    assigned_to: String(item.assigned_to ?? ""),
    details: item.details ?? {},
  }));
}

export function mapApprovalsResponse(input: unknown): Approval[] {
  const items = Array.isArray((input as any)?.items) ? (input as any).items : [];
  return items.map((item: any) => ({
    approval_id: String(item.approval_id ?? ""),
    status: String(item.status ?? "pending"),
    reason: String(item.reason ?? ""),
    required_role: String(item.required_role ?? ""),
  }));
}
