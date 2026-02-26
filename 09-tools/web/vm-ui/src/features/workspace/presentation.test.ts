import { describe, expect, it } from "vitest";
import { toHumanRunName, toHumanStatus } from "./presentation";

describe("run presentation", () => {
  it("builds human run names", () => {
    const name = toHumanRunName({
      index: 2,
      requestText: "conteudo redes sociais",
      createdAt: "2026-02-26T14:20:00Z",
    });
    expect(name).toContain("Versao 2");
  });

  it("maps run status", () => {
    expect(toHumanStatus("waiting_approval")).toBe("Aguardando revisao");
  });
});
