import type { QualityScore } from "./types";

const CTA_KEYWORDS = ["cta", "clique", "cadastre", "agende", "compre", "baixe", "fale", "responda", "comece"];
const ACTION_VERBS = ["defina", "liste", "priorize", "execute", "publique", "teste", "meca", "ajuste", "otimize"];

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function countKeywordHits(text: string, keywords: string[]): number {
  return keywords.reduce((hits, keyword) => (text.includes(keyword) ? hits + 1 : hits), 0);
}

export function computeQualityScore(markdown: string): QualityScore {
  const text = markdown.trim();
  const lowered = text.toLowerCase();
  const wordCount = (text.match(/\p{L}[\p{L}\p{N}]*/gu) ?? []).length;
  const headingCount = (text.match(/^#{1,6}\s+/gm) ?? []).length;
  const listCount = (text.match(/^\s*(?:[-*+]|\\d+[.)])\s+/gm) ?? []).length;
  const sentenceCount = Math.max(1, text.split(/[.!?]\s+/).filter((line) => line.trim().length > 0).length);
  const avgWordsPerSentence = wordCount / sentenceCount;
  const ctaHits = countKeywordHits(lowered, CTA_KEYWORDS);
  const actionHits = countKeywordHits(lowered, ACTION_VERBS);

  const completudeBase =
    wordCount >= 220 ? 85 : wordCount >= 140 ? 70 : wordCount >= 80 ? 55 : wordCount >= 40 ? 40 : 20;
  const completude = clampScore(completudeBase + Math.min(15, headingCount * 5));
  const estrutura = clampScore(headingCount * 22 + listCount * 10 + (headingCount >= 3 ? 10 : 0));

  const clarezaBase =
    wordCount === 0
      ? 0
      : avgWordsPerSentence >= 6 && avgWordsPerSentence <= 24
        ? 80
        : avgWordsPerSentence <= 32
          ? 65
          : 45;
  const clareza = clampScore(clarezaBase + (listCount > 0 ? 10 : 0) + (wordCount < 20 ? -20 : 0));
  const cta = clampScore(ctaHits * 30 + actionHits * 8);
  const acionabilidade = clampScore(listCount * 20 + actionHits * 15 + ctaHits * 10);

  const criteria = { completude, estrutura, clareza, cta, acionabilidade };
  const overall = clampScore(
    (criteria.completude + criteria.estrutura + criteria.clareza + criteria.cta + criteria.acionabilidade) / 5
  );

  const recommendations: string[] = [];
  if (criteria.completude < 60) recommendations.push("Aumente a completude com mais contexto e detalhamento.");
  if (criteria.estrutura < 60) recommendations.push("Estruture com titulos, subtitulos e blocos bem definidos.");
  if (criteria.clareza < 60) recommendations.push("Simplifique frases e mantenha orientacoes mais objetivas.");
  if (criteria.cta < 60) recommendations.push("Inclua um CTA explicito com proximo passo claro.");
  if (criteria.acionabilidade < 60) recommendations.push("Adicione passos acionaveis com verbos de acao.");

  return {
    overall,
    criteria,
    recommendations,
    source: "heuristic",
  };
}
