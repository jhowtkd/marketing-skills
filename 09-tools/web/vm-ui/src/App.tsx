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
    <div data-vm-ui="react" className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-lg font-semibold">VM Studio</h1>
              <p className="mt-1 text-xs text-slate-500">
                {activeBrandId ? `Cliente: ${activeBrandId}` : "Cliente: —"}
                {" · "}
                {activeProjectId ? `Campanha: ${activeProjectId}` : "Campanha: —"}
                {" · "}
                {activeThreadId ? `Job: ${activeThreadId}` : "Job: —"}
              </p>
            </div>
            <label className="inline-flex items-center gap-2 text-sm text-slate-700">
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
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        <div className="grid gap-4 lg:grid-cols-12">
          <aside className="lg:col-span-3">
            <NavigationPanel
              activeBrandId={activeBrandId}
              activeProjectId={activeProjectId}
              activeThreadId={activeThreadId}
              onSelectBrand={handleSelectBrand}
              onSelectProject={handleSelectProject}
              onSelectThread={handleSelectThread}
            />
          </aside>

          <section className="lg:col-span-6">
            <WorkspacePanel
              activeThreadId={activeThreadId}
              activeRunId={activeRunId}
              onSelectRun={setActiveRunId}
              devMode={devMode}
            />
          </section>

          <aside className="lg:col-span-3">
            <InboxPanel activeThreadId={activeThreadId} activeRunId={activeRunId} devMode={devMode} />
          </aside>
        </div>
      </main>
    </div>
  );
}

