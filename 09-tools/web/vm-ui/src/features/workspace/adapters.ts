export type TimelineEvent = {
  event_id: string;
  event_type: string;
  created_at: string;
  payload: unknown;
};

export function mapTimelineResponse(input: unknown): TimelineEvent[] {
  const items = Array.isArray((input as any)?.items) ? (input as any).items : [];
  return items.map((item: any) => ({
    event_id: String(item.event_id ?? ""),
    event_type: String(item.event_type ?? "UnknownEvent"),
    created_at: String(item.occurred_at ?? item.created_at ?? ""),
    payload: item.payload ?? {},
  }));
}
