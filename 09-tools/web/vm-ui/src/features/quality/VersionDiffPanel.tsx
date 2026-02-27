import { computeLineDiff } from "./diff";

type Props = {
  baselineText: string;
  currentText: string;
};

export default function VersionDiffPanel({ baselineText, currentText }: Props) {
  const diff = computeLineDiff(baselineText, currentText);
  const addedLines = diff.filter((line) => line.type === "added");
  const removedLines = diff.filter((line) => line.type === "removed");

  return (
    <section className="rounded-[1.25rem] border border-slate-200 bg-white p-4">
      <p className="text-[0.7rem] font-semibold uppercase tracking-[0.16em] text-slate-500">Comparacao textual</p>
      <h3 className="mt-1 text-sm font-semibold text-slate-900">Diff entre versoes</h3>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-3">
          <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">Blocos adicionados</h4>
          {addedLines.length === 0 ? (
            <p className="mt-2 text-sm text-emerald-700/80">Nenhuma adicao detectada.</p>
          ) : (
            <ul className="mt-2 space-y-1">
              {addedLines.map((line, index) => (
                <li key={`${line.text}-${index}`} className="rounded border border-emerald-100 bg-white/90 px-2 py-1 text-sm text-emerald-900">
                  {line.text}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-rose-200 bg-rose-50/60 p-3">
          <h4 className="text-xs font-semibold uppercase tracking-[0.14em] text-rose-700">Blocos removidos</h4>
          {removedLines.length === 0 ? (
            <p className="mt-2 text-sm text-rose-700/80">Nenhuma remocao detectada.</p>
          ) : (
            <ul className="mt-2 space-y-1">
              {removedLines.map((line, index) => (
                <li key={`${line.text}-${index}`} className="rounded border border-rose-100 bg-white/90 px-2 py-1 text-sm text-rose-900">
                  {line.text}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
