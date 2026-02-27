import { compareScores } from "./compare";
import type { QualityCriteriaKey, QualityScore } from "./types";

type Props = {
  current: QualityScore;
  baseline?: QualityScore | null;
};

const CRITERIA_LABELS: Record<QualityCriteriaKey, string> = {
  completude: "Completude",
  estrutura: "Estrutura",
  clareza: "Clareza",
  cta: "CTA",
  acionabilidade: "Acionabilidade",
};

function formatDelta(value: number): string {
  return value > 0 ? `+${value}` : `${value}`;
}

export default function QualityScoreCard({ current, baseline = null }: Props) {
  const delta = baseline ? compareScores(current, baseline) : null;

  return (
    <section className="rounded-[1.25rem] border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-slate-500">Qualidade</p>
          <h3 className="mt-1 text-sm font-semibold text-slate-900">Score geral</h3>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold text-slate-900">{current.overall}</p>
          {delta ? (
            <p
              className={`text-xs font-semibold ${
                delta.overallDelta > 0 ? "text-emerald-600" : delta.overallDelta < 0 ? "text-rose-600" : "text-slate-500"
              }`}
            >
              {formatDelta(delta.overallDelta)}
            </p>
          ) : (
            <p className="text-xs text-slate-500">Sem baseline</p>
          )}
        </div>
      </div>

      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        {(Object.keys(CRITERIA_LABELS) as QualityCriteriaKey[]).map((key) => (
          <div key={key} className="rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2">
            <dt className="text-xs uppercase tracking-[0.12em] text-slate-500">{CRITERIA_LABELS[key]}</dt>
            <dd className="mt-1 flex items-center justify-between text-sm font-medium text-slate-900">
              <span>{current.criteria[key]}</span>
              {delta ? (
                <span
                  className={
                    delta.criteriaDelta[key] > 0
                      ? "text-emerald-600"
                      : delta.criteriaDelta[key] < 0
                        ? "text-rose-600"
                        : "text-slate-500"
                  }
                >
                  {formatDelta(delta.criteriaDelta[key])}
                </span>
              ) : null}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
