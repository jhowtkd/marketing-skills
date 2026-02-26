import { useEffect, useMemo, useState, type FormEvent } from "react";

import { fetchJson, postJson } from "./api/client";
import {
  ENDPOINT_BRANDS,
  ENDPOINT_PROJECTS,
  ENDPOINT_THREADS,
} from "./api/endpoints";
import type { Brand, BrandsResponse, Project, ProjectsResponse, Thread, ThreadsResponse } from "./api/types";

export default function App() {
  const [error, setError] = useState<string | null>(null);

  const [brands, setBrands] = useState<Brand[]>([]);
  const [activeBrandId, setActiveBrandId] = useState<string | null>(null);

  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  const activeBrand = useMemo(
    () => brands.find((b) => b.brand_id === activeBrandId) || null,
    [brands, activeBrandId]
  );
  const activeProject = useMemo(
    () => projects.find((p) => p.project_id === activeProjectId) || null,
    [projects, activeProjectId]
  );

  async function loadBrands(): Promise<void> {
    const body = await fetchJson<BrandsResponse>(ENDPOINT_BRANDS);
    const nextBrands = Array.isArray(body.brands) ? body.brands : [];
    setBrands(nextBrands);
    setActiveBrandId((prev) => {
      if (prev && nextBrands.some((b) => b.brand_id === prev)) return prev;
      return nextBrands[0]?.brand_id ?? null;
    });
  }

  async function loadProjects(brandId: string): Promise<void> {
    const body = await fetchJson<ProjectsResponse>(
      `${ENDPOINT_PROJECTS}?brand_id=${encodeURIComponent(brandId)}`
    );
    const nextProjects = Array.isArray(body.projects) ? body.projects : [];
    setProjects(nextProjects);
    setActiveProjectId((prev) => {
      if (prev && nextProjects.some((p) => p.project_id === prev)) return prev;
      return nextProjects[0]?.project_id ?? null;
    });
  }

  async function loadThreads(projectId: string): Promise<void> {
    const body = await fetchJson<ThreadsResponse>(
      `${ENDPOINT_THREADS}?project_id=${encodeURIComponent(projectId)}`
    );
    const nextThreads = Array.isArray(body.threads) ? body.threads : [];
    setThreads(nextThreads);
    setActiveThreadId((prev) => {
      if (prev && nextThreads.some((t) => t.thread_id === prev)) return prev;
      return nextThreads[0]?.thread_id ?? null;
    });
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setError(null);
        await loadBrands();
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!activeBrandId) {
        setProjects([]);
        setActiveProjectId(null);
        return;
      }
      try {
        setError(null);
        await loadProjects(activeBrandId);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeBrandId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!activeProjectId) {
        setThreads([]);
        setActiveThreadId(null);
        return;
      }
      try {
        setError(null);
        await loadThreads(activeProjectId);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeProjectId]);

  const [newBrandName, setNewBrandName] = useState("");

  async function handleCreateBrand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newBrandName.trim();
    if (!name) return;
    try {
      setError(null);
      await postJson<{ brand_id: string; name: string }>(
        ENDPOINT_BRANDS,
        { name },
        "brand-create"
      );
      setNewBrandName("");
      await loadBrands();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div data-vm-ui="react" className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-lg font-semibold text-slate-900">VM Workspace</h1>
          <p className="mt-1 text-sm text-slate-500">
            {activeBrand?.name ? `Marca: ${activeBrand.name}` : "Selecione uma marca"}
            {activeProject?.name ? ` · Projeto: ${activeProject.name}` : ""}
          </p>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        {error ? (
          <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
            {error}
          </div>
        ) : null}
        <div className="grid gap-4 lg:grid-cols-12">
          <aside className="lg:col-span-4 space-y-4">
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold text-slate-900">Marcas</h2>
              </div>
              <form onSubmit={handleCreateBrand} className="flex gap-2">
                <input
                  value={newBrandName}
                  onChange={(e) => setNewBrandName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  placeholder="Nova marca"
                />
                <button
                  type="submit"
                  className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white"
                >
                  Criar
                </button>
              </form>
              <div className="mt-3 space-y-1">
                {brands.length ? (
                  brands.map((b) => (
                    <button
                      key={b.brand_id}
                      type="button"
                      onClick={() => setActiveBrandId(b.brand_id)}
                      className={[
                        "w-full rounded-lg border px-3 py-2 text-left text-sm",
                        b.brand_id === activeBrandId
                          ? "border-blue-200 bg-blue-50 text-blue-900"
                          : "border-slate-200 bg-white text-slate-800 hover:bg-slate-50",
                      ].join(" ")}
                    >
                      {b.name}
                      <span className="ml-2 text-xs text-slate-400">{b.brand_id}</span>
                    </button>
                  ))
                ) : (
                  <div className="text-sm text-slate-500">Sem marcas ainda.</div>
                )}
              </div>
            </section>

            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">Projetos</h2>
              <div className="mt-3 space-y-1">
                {projects.length ? (
                  projects.map((p) => (
                    <button
                      key={p.project_id}
                      type="button"
                      onClick={() => setActiveProjectId(p.project_id)}
                      className={[
                        "w-full rounded-lg border px-3 py-2 text-left text-sm",
                        p.project_id === activeProjectId
                          ? "border-blue-200 bg-blue-50 text-blue-900"
                          : "border-slate-200 bg-white text-slate-800 hover:bg-slate-50",
                      ].join(" ")}
                    >
                      {p.name}
                      <span className="ml-2 text-xs text-slate-400">{p.project_id}</span>
                    </button>
                  ))
                ) : (
                  <div className="text-sm text-slate-500">
                    {activeBrandId ? "Sem projetos ainda." : "Selecione uma marca."}
                  </div>
                )}
              </div>
            </section>
          </aside>

          <section className="lg:col-span-8 space-y-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">Planos (Threads)</h2>
              <div className="mt-3 space-y-1">
                {threads.length ? (
                  threads.map((t) => (
                    <button
                      key={t.thread_id}
                      type="button"
                      onClick={() => setActiveThreadId(t.thread_id)}
                      className={[
                        "w-full rounded-lg border px-3 py-2 text-left text-sm",
                        t.thread_id === activeThreadId
                          ? "border-blue-200 bg-blue-50 text-blue-900"
                          : "border-slate-200 bg-white text-slate-800 hover:bg-slate-50",
                      ].join(" ")}
                    >
                      {t.title}
                      <span className="ml-2 text-xs text-slate-400">{t.thread_id}</span>
                    </button>
                  ))
                ) : (
                  <div className="text-sm text-slate-500">
                    {activeProjectId ? "Sem threads ainda." : "Selecione um projeto."}
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
