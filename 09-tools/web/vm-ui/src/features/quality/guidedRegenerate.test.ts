import { describe, expect, it } from "vitest";
import { buildGuidedRequest } from "./guidedRegenerate";

describe("buildGuidedRequest", () => {
  it("builds request text using presets and user guidance", () => {
    const text = buildGuidedRequest({
      baseRequest: "Plano de lancamento",
      presets: ["mais_profundo", "mais_persuasivo"],
      userGuidance: "focar em ICP B2B",
      weakPoints: ["CTA fraco"],
    });

    expect(text).toContain("Plano de lancamento");
    expect(text).toContain("ICP B2B");
    expect(text).toContain("CTA fraco");
  });
});
