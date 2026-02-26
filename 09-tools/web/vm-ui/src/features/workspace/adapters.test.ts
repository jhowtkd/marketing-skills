import { describe, expect, it } from "vitest";
import { mapTimelineResponse } from "./adapters";

describe("mapTimelineResponse", () => {
  it("maps API v2 items into timeline events", () => {
    const payload = {
      items: [
        {
          event_id: "evt-1",
          event_type: "WorkflowRunStarted",
          occurred_at: "2026-02-26T10:00:00Z",
          payload: { run_id: "run-1" },
        },
      ],
    };
    const events = mapTimelineResponse(payload);
    expect(events).toHaveLength(1);
    expect(events[0].created_at).toBe("2026-02-26T10:00:00Z");
  });
});
