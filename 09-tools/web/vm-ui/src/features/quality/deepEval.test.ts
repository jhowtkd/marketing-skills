import { describe, expect, it, vi, beforeEach } from "vitest";
import { requestDeepEvaluationForRun } from "../workspace/useWorkspace";
import { QualityApi } from "../../api/typed-client";

describe("requestDeepEvaluationForRun", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("requests deep evaluation on the correct endpoint", async () => {
    const evaluateSpy = vi.spyOn(QualityApi, "evaluate").mockResolvedValue({
      score: {
        overall: 91,
        criteria: {
          completude: 90,
          estrutura: 92,
          clareza: 88,
          cta: 94,
          acionabilidade: 91,
        },
        recommendations: [],
        source: "deep",
      },
      fallback_applied: false,
    });

    const result = await requestDeepEvaluationForRun({
      runId: "run-123",
      artifactText: "# Plano\n## CTA\nComprar agora",
    });

    expect(evaluateSpy).toHaveBeenCalledWith("run-123");
    expect(result.status).toBe("ready");
    expect(result.score?.source).toBe("deep");
  });

  it("falls back to local heuristic score when deep evaluation fails", async () => {
    vi.spyOn(QualityApi, "evaluate").mockRejectedValue(new Error("network down"));

    const result = await requestDeepEvaluationForRun({
      runId: "run-456",
      artifactText: "texto curto",
    });

    expect(result.status).toBe("error");
    expect(result.score?.source).toBe("heuristic");
    expect(result.fallbackApplied).toBe(true);
    expect(result.error).toContain("network down");
  });
});
