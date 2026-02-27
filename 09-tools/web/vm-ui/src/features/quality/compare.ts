import type { QualityCriteriaKey, QualityScore } from "./types";

export type QualityDelta = {
  overallDelta: number;
  criteriaDelta: Record<QualityCriteriaKey, number>;
};

export function compareScores(current: QualityScore, baseline: QualityScore): QualityDelta {
  return {
    overallDelta: current.overall - baseline.overall,
    criteriaDelta: {
      completude: current.criteria.completude - baseline.criteria.completude,
      estrutura: current.criteria.estrutura - baseline.criteria.estrutura,
      clareza: current.criteria.clareza - baseline.criteria.clareza,
      cta: current.criteria.cta - baseline.criteria.cta,
      acionabilidade: current.criteria.acionabilidade - baseline.criteria.acionabilidade,
    },
  };
}
