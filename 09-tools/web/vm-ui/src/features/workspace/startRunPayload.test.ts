import { describe, expect, it } from "vitest";
import { buildStartRunPayload } from "./useWorkspace";

describe("buildStartRunPayload", () => {
  it("keeps user request_text instead of hardcoded text", () => {
    const payload = buildStartRunPayload({ mode: "content_calendar", requestText: "campanha lancamento 2026" });
    expect(payload.request_text).toBe("campanha lancamento 2026");
    expect(payload.mode).toBe("content_calendar");
  });
});
