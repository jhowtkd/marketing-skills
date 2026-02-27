export type QualityCriteriaKey = "completude" | "estrutura" | "clareza" | "cta" | "acionabilidade";

export type QualityScore = {
  overall: number;
  criteria: Record<QualityCriteriaKey, number>;
  recommendations: string[];
  source: "heuristic" | "deep";
};
