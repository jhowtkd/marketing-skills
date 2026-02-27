import { describe, expect, it } from "vitest";
import { compareScores } from "./compare";

describe("compareScores", () => {
  it("computes criteria deltas between versions", () => {
    const result = compareScores(
      {
        overall: 80,
        criteria: { completude: 90, estrutura: 80, clareza: 70, cta: 80, acionabilidade: 80 },
        recommendations: [],
        source: "heuristic",
      },
      {
        overall: 60,
        criteria: { completude: 50, estrutura: 60, clareza: 60, cta: 70, acionabilidade: 60 },
        recommendations: [],
        source: "heuristic",
      }
    );

    expect(result.overallDelta).toBe(20);
    expect(result.criteriaDelta.completude).toBe(40);
  });
});
