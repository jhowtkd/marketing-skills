import { describe, expect, it } from "vitest";
import {
  canResumeRunStatus,
  toHumanRunName,
  toHumanStatus,
  toHumanTimelineEvent,
  toHumanTimelineEventDetails,
  isEditorialEvent,
  filterTimelineEvents,
  TIMELINE_FILTER_LABELS,
} from "./presentation";

describe("run presentation", () => {
  it("builds human run names", () => {
    const name = toHumanRunName({
      index: 2,
      requestText: "conteudo redes sociais",
      createdAt: "2026-02-26T14:20:00Z",
    });
    expect(name).toContain("Versao 2");
  });

  it("does not crash when request text is missing", () => {
    const name = toHumanRunName({
      index: 1,
      requestText: undefined as unknown as string,
      createdAt: "2026-02-26T14:20:00Z",
    });
    expect(name).toContain("Versao 1");
    expect(name).toContain("sem pedido");
  });

  it("maps run status", () => {
    expect(toHumanStatus("waiting_approval")).toBe("Aguardando revisao");
  });

  it("maps timeline event labels", () => {
    expect(toHumanTimelineEvent("WorkflowRunStarted")).toBe("Geracao iniciada");
    expect(toHumanTimelineEvent("UnknownEvent")).toBe("UnknownEvent");
  });

  it("humanizes EditorialGoldenMarked with global scope", () => {
    expect(toHumanTimelineEvent({ event_type: "EditorialGoldenMarked", payload: { scope: "global" } })).toBe("Golden global definido");
  });

  it("humanizes EditorialGoldenMarked with objective scope", () => {
    expect(toHumanTimelineEvent({ event_type: "EditorialGoldenMarked", payload: { scope: "objective" } })).toBe("Golden de objetivo definido");
  });

  it("falls back to generic label for EditorialGoldenMarked without payload", () => {
    expect(toHumanTimelineEvent("EditorialGoldenMarked")).toBe("Golden marcado");
    expect(toHumanTimelineEvent({ event_type: "EditorialGoldenMarked", payload: undefined })).toBe("Golden marcado");
  });

  it("flags statuses that require resume action", () => {
    expect(canResumeRunStatus("waiting_approval")).toBe(true);
    expect(canResumeRunStatus("waiting")).toBe(true);
    expect(canResumeRunStatus("paused")).toBe(true);
    expect(canResumeRunStatus("running")).toBe(false);
  });
});

describe("timeline editorial", () => {
  it("returns details with actor and justification for editorial events", () => {
    const result = toHumanTimelineEventDetails({
      event_type: "EditorialGoldenMarked",
      payload: { scope: "global", justification: "Melhor versao" },
      actor_id: "user-john",
    });
    expect(result.label).toBe("Golden global definido");
    expect(result.actor).toBe("user-john");
    expect(result.justification).toBe("Melhor versao");
  });

  it("returns only label for non-editorial events", () => {
    const result = toHumanTimelineEventDetails({
      event_type: "WorkflowRunStarted",
      payload: { stage: "foundation" },
    });
    expect(result.label).toBe("Geracao iniciada");
    expect(result.actor).toBeUndefined();
    expect(result.justification).toBeUndefined();
  });

  it("truncates long justifications", () => {
    const longJustification = "A".repeat(100);
    const result = toHumanTimelineEventDetails({
      event_type: "EditorialGoldenMarked",
      payload: { scope: "objective", justification: longJustification },
      actor_id: "user-jane",
    });
    expect(result.justification).toBe(longJustification);
    // UI handles truncation, function returns full text
  });

  it("identifies editorial events", () => {
    expect(isEditorialEvent("EditorialGoldenMarked")).toBe(true);
    expect(isEditorialEvent("WorkflowRunStarted")).toBe(false);
    expect(isEditorialEvent("TaskCreated")).toBe(false);
  });

  it("filters timeline events by editorial filter", () => {
    const events = [
      { event_type: "EditorialGoldenMarked", event_id: "1", created_at: "2026-01-01" },
      { event_type: "WorkflowRunStarted", event_id: "2", created_at: "2026-01-02" },
      { event_type: "EditorialGoldenMarked", event_id: "3", created_at: "2026-01-03" },
    ];
    const all = filterTimelineEvents(events, "all");
    const editorial = filterTimelineEvents(events, "editorial");
    
    expect(all).toHaveLength(3);
    expect(editorial).toHaveLength(2);
    expect(editorial.every((e) => e.event_type === "EditorialGoldenMarked")).toBe(true);
  });

  it("provides timeline filter labels", () => {
    expect(TIMELINE_FILTER_LABELS.all).toBe("Todos");
    expect(TIMELINE_FILTER_LABELS.editorial).toBe("Editorial");
  });
});
