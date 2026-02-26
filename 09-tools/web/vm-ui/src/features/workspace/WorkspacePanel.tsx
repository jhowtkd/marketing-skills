type MaybeId = string | null;

type Props = {
  activeThreadId: MaybeId;
  activeRunId: MaybeId;
  onSelectRun: (runId: MaybeId) => void;
  devMode: boolean;
};

export default function WorkspacePanel({ activeThreadId, activeRunId, onSelectRun, devMode }: Props) {
  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Studio</h2>
        <p className="mt-2 text-sm text-slate-600">
          {activeThreadId
            ? "Thread selecionada. O proximo passo e rodar um workflow e acompanhar o progresso."
            : "Selecione uma thread na coluna da esquerda para comecar."}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!activeThreadId}
            className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Criar plano
          </button>
          <button
            type="button"
            disabled={!activeThreadId}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900 disabled:opacity-50"
          >
            Rodar workflow
          </button>
          {activeRunId ? (
            <button
              type="button"
              onClick={() => onSelectRun(null)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-900"
            >
              Limpar run ativa
            </button>
          ) : null}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Execucoes</h2>
        <p className="mt-2 text-sm text-slate-600">
          Em breve: lista de runs, detalhe, timeline e artefatos.
        </p>
        {devMode ? (
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
        ) : null}
      </section>
    </div>
  );
}

