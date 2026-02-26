type MaybeId = string | null;

type Props = {
  activeThreadId: MaybeId;
  activeRunId: MaybeId;
  devMode: boolean;
};

export default function InboxPanel({ activeThreadId, activeRunId, devMode }: Props) {
  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Inbox</h2>
        <p className="mt-2 text-sm text-slate-600">
          Em breve: tasks, approvals e artefatos vinculados a thread/run.
        </p>
      </section>

      {devMode ? (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Debug</h2>
          <pre className="mt-3 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
{JSON.stringify(
  {
    activeThreadId,
    activeRunId,
  },
  null,
  2
)}
          </pre>
        </section>
      ) : null}
    </div>
  );
}

