import { describe, expect, it } from "vitest";
import { computeQualityScore } from "./score";

describe("computeQualityScore", () => {
  it("scores structured markdown higher than sparse text", () => {
    const structured = "# Titulo\n## Problema\nTexto\n## Solucao\nTexto\n## CTA\nAcao";
    const sparse = "texto curto sem estrutura";

    const a = computeQualityScore(structured);
    const b = computeQualityScore(sparse);

    expect(a.overall).toBeGreaterThan(b.overall);
  });

  it("returns actionable recommendations when criteria are weak", () => {
    const result = computeQualityScore("texto curto");
    expect(result.recommendations.length).toBeGreaterThan(0);
  });
});
