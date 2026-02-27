import { describe, expect, it } from "vitest";
import { canResumeRunStatus, toHumanRunName, toHumanStatus, toHumanTimelineEvent } from "./presentation";

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
