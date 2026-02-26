import { useEffect, useState } from "react";

import InboxPanel from "./features/inbox/InboxPanel";
import NavigationPanel from "./features/navigation/NavigationPanel";
import WorkspacePanel from "./features/workspace/WorkspacePanel";

type MaybeId = string | null;

function readDevMode(): boolean {
  try {
    return window.localStorage.getItem("vm.devMode") === "1";
  } catch {
    return false;
  }
}

function writeDevMode(value: boolean): void {
  try {
    window.localStorage.setItem("vm.devMode", value ? "1" : "0");
  } catch {
    // ignore
  }
}

function formatContextValue(value: MaybeId, filledLabel: string): string {
  return value ? filledLabel : "Nao definido";
}

export default function App() {
  const [activeBrandId, setActiveBrandId] = useState<MaybeId>(null);
  const [activeProjectId, setActiveProjectId] = useState<MaybeId>(null);
  const [activeThreadId, setActiveThreadId] = useState<MaybeId>(null);
  const [activeRunId, setActiveRunId] = useState<MaybeId>(null);

  const [devMode, setDevMode] = useState<boolean>(readDevMode);

  useEffect(() => {
    writeDevMode(devMode);
  }, [devMode]);

  function handleSelectBrand(nextBrandId: MaybeId): void {
    setActiveBrandId(nextBrandId);
    setActiveProjectId(null);
    setActiveThreadId(null);
    setActiveRunId(null);
  }

  function handleSelectProject(nextProjectId: MaybeId): void {
    setActiveProjectId(nextProjectId);
    setActiveThreadId(null);
    setActiveRunId(null);
  }

  function handleSelectThread(nextThreadId: MaybeId): void {
    setActiveThreadId(nextThreadId);
    setActiveRunId(null);
  }

  return (
    <div data-vm-ui="react" className="min-h-screen bg-[var(--vm-bg)] text-[var(--vm-ink)]">
      <header className="border-b border-[color:var(--vm-line)] bg-[color:var(--vm-surface)]/95 backdrop-blur">
        <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-5 px-4 py-5 lg:px-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-[var(--vm-primary)]">
                Deliverable-first studio
              </p>
              <div>
                <h1 className="font-serif text-3xl leading-none text-[var(--vm-ink)] sm:text-4xl">VM Studio</h1>
                <p className="mt-2 max-w-2xl text-sm text-[var(--vm-muted)]">
                  Preview da versao ativa no centro, contexto editavel no topo e acoes operacionais ao lado.
                </p>
              </div>
            </div>

            <div className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/80 p-3 shadow-[0_16px_40px_rgba(22,32,51,0.08)]">
              <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-[var(--vm-muted)]">
                Ferramentas
              </p>
              <label className="mt-3 inline-flex items-center gap-2 text-sm text-[var(--vm-ink)]">
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-primary"
                  checked={devMode}
                  onChange={(e) => setDevMode(e.target.checked)}
                />
                Dev mode
              </label>
            </div>
          </div>

          <section
            role="region"
            aria-label="Contexto do studio"
            className="rounded-[1.75rem] border border-[color:var(--vm-line)] bg-[color:var(--vm-surface)] p-4 shadow-[0_18px_45px_rgba(22,32,51,0.08)]"
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
                  Contexto ativo
                </p>
                <p className="mt-2 text-sm text-[var(--vm-muted)]">
                  Selecione cliente, campanha e job na navegacao reduzida para atualizar o canvas principal.
                </p>
              </div>
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--vm-muted)]">
                Dev mode fica secundario para manter a leitura editorial.
              </p>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-[1.25rem] border border-[color:var(--vm-line)] bg-white/85 px-4 py-3">
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-[var(--vm-muted)]">
                  Cliente
                </p>
                <p className="mt-2 text-base font-semibold text-[var(--vm-ink)]">
                  {formatContextValue(activeBrandId, devMode ? activeBrandId : "Cliente selecionado")}
                </p>
              </div>
              <div className="rounded-[1.25rem] border border-[color:var(--vm-line)] bg-white/85 px-4 py-3">
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-[var(--vm-muted)]">
                  Campanha
                </p>
                <p className="mt-2 text-base font-semibold text-[var(--vm-ink)]">
                  {formatContextValue(activeProjectId, devMode ? activeProjectId : "Campanha selecionada")}
                </p>
              </div>
              <div className="rounded-[1.25rem] border border-[color:var(--vm-line)] bg-white/85 px-4 py-3">
                <p className="text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-[var(--vm-muted)]">
                  Job
                </p>
                <p className="mt-2 text-base font-semibold text-[var(--vm-ink)]">
                  {formatContextValue(activeThreadId, devMode ? activeThreadId : "Job selecionado")}
                </p>
              </div>
            </div>
          </section>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1600px] px-4 py-6 lg:px-6 lg:py-8">
        <div className="grid gap-5 xl:grid-cols-[minmax(280px,0.95fr)_minmax(0,1.6fr)_minmax(280px,0.95fr)]">
          <section
            role="region"
            aria-label="Navegacao do studio"
            className="rounded-[1.75rem] border border-[color:var(--vm-line)] bg-[color:var(--vm-surface)] p-4 shadow-[0_18px_45px_rgba(22,32,51,0.08)]"
          >
            <div className="mb-4 flex items-end justify-between gap-3">
              <div>
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-[var(--vm-primary)]">
                  Navegacao
                </p>
                <h2 className="mt-2 font-serif text-2xl text-[var(--vm-ink)]">Studio rail</h2>
              </div>
            </div>
            <NavigationPanel
              activeBrandId={activeBrandId}
              activeProjectId={activeProjectId}
              activeThreadId={activeThreadId}
              devMode={devMode}
              onSelectBrand={handleSelectBrand}
              onSelectProject={handleSelectProject}
              onSelectThread={handleSelectThread}
            />
          </section>

          <section
            role="region"
            aria-label="Canvas do entregavel"
            className="rounded-[2rem] border border-[color:var(--vm-line)] bg-[color:var(--vm-surface)] p-4 shadow-[0_20px_48px_rgba(22,32,51,0.1)] sm:p-5"
          >
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-[var(--vm-primary)]">
                  Canvas central
                </p>
                <h2 className="mt-2 font-serif text-2xl text-[var(--vm-ink)]">Canvas do entregavel</h2>
              </div>
              <p className="max-w-xs text-right text-xs uppercase tracking-[0.16em] text-[var(--vm-muted)]">
                A versao ativa deve dominar a leitura.
              </p>
            </div>
            <WorkspacePanel
              activeThreadId={activeThreadId}
              activeRunId={activeRunId}
              onSelectRun={setActiveRunId}
              devMode={devMode}
            />
          </section>

          <section
            role="region"
            aria-label="Action rail da versao"
            className="rounded-[1.75rem] border border-[color:var(--vm-line)] bg-[color:var(--vm-surface)] p-4 shadow-[0_18px_45px_rgba(22,32,51,0.08)]"
          >
            <div className="mb-4 flex items-end justify-between gap-3">
              <div>
                <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-[var(--vm-primary)]">
                  Action rail
                </p>
                <h2 className="mt-2 font-serif text-2xl text-[var(--vm-ink)]">Pendencias da versao</h2>
              </div>
            </div>
            <InboxPanel activeThreadId={activeThreadId} activeRunId={activeRunId} devMode={devMode} />
          </section>
        </div>
      </main>
    </div>
  );
}
