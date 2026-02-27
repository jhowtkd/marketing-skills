import { describe, expect, it, vi } from "vitest";
import { requestDeepEvaluationForRun } from "../workspace/useWorkspace";

describe("requestDeepEvaluationForRun", () => {
  it("requests deep evaluation on the correct endpoint", async () => {
    const post = vi.fn().mockResolvedValue({
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
      post,
    });

    expect(post).toHaveBeenCalledWith(
      "/api/v2/workflow-runs/run-123/quality-evaluation",
      { depth: "deep", rubric_version: "v1" },
      "quality"
    );
    expect(result.status).toBe("ready");
    expect(result.score?.source).toBe("deep");
  });

  it("falls back to local heuristic score when deep evaluation fails", async () => {
    const post = vi.fn().mockRejectedValue(new Error("network down"));

    const result = await requestDeepEvaluationForRun({
      runId: "run-456",
      artifactText: "texto curto",
      post,
    });

    expect(result.status).toBe("error");
    expect(result.score?.source).toBe("heuristic");
    expect(result.fallbackApplied).toBe(true);
    expect(result.error).toContain("network down");
  });
});
