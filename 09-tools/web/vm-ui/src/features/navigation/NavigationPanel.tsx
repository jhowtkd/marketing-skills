import { useEffect, useState, type FormEvent } from "react";

import { fetchJson, postJson } from "../../api/client";
import { ENDPOINT_BRANDS, ENDPOINT_PROJECTS, ENDPOINT_THREADS } from "../../api/endpoints";
import type { Brand, BrandsResponse, Project, ProjectsResponse, Thread, ThreadsResponse } from "../../api/types";

type MaybeId = string | null;

type Props = {
  activeBrandId: MaybeId;
  activeProjectId: MaybeId;
  activeThreadId: MaybeId;
  onSelectBrand: (brandId: MaybeId) => void;
  onSelectProject: (projectId: MaybeId) => void;
  onSelectThread: (threadId: MaybeId) => void;
};

export default function NavigationPanel({
  activeBrandId,
  activeProjectId,
  activeThreadId,
  onSelectBrand,
  onSelectProject,
  onSelectThread,
}: Props) {
  const [error, setError] = useState<string | null>(null);

  const [brands, setBrands] = useState<Brand[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [threads, setThreads] = useState<Thread[]>([]);

  async function loadBrands(): Promise<void> {
    const body = await fetchJson<BrandsResponse>(ENDPOINT_BRANDS);
    const nextBrands = Array.isArray(body.brands) ? body.brands : [];
    setBrands(nextBrands);
    const nextActive =
      activeBrandId && nextBrands.some((b) => b.brand_id === activeBrandId)
        ? activeBrandId
        : nextBrands[0]?.brand_id ?? null;
    if (nextActive !== activeBrandId) onSelectBrand(nextActive);
  }

  async function loadProjects(brandId: string): Promise<void> {
    const body = await fetchJson<ProjectsResponse>(
      `${ENDPOINT_PROJECTS}?brand_id=${encodeURIComponent(brandId)}`
    );
    const nextProjects = Array.isArray(body.projects) ? body.projects : [];
    setProjects(nextProjects);
    const nextActive =
      activeProjectId && nextProjects.some((p) => p.project_id === activeProjectId)
        ? activeProjectId
        : nextProjects[0]?.project_id ?? null;
    if (nextActive !== activeProjectId) onSelectProject(nextActive);
  }

  async function loadThreads(projectId: string): Promise<void> {
    const body = await fetchJson<ThreadsResponse>(
      `${ENDPOINT_THREADS}?project_id=${encodeURIComponent(projectId)}`
    );
    const nextThreads = Array.isArray(body.threads) ? body.threads : [];
    setThreads(nextThreads);
    const nextActive =
      activeThreadId && nextThreads.some((t) => t.thread_id === activeThreadId)
        ? activeThreadId
        : nextThreads[0]?.thread_id ?? null;
    if (nextActive !== activeThreadId) onSelectThread(nextActive);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!activeBrandId) {
        setProjects([]);
        setThreads([]);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeBrandId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!activeProjectId) {
        setThreads([]);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId]);

  const [newBrandName, setNewBrandName] = useState("");

  async function handleCreateBrand(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newBrandName.trim();
    if (!name) return;
    try {
      setError(null);
      await postJson<{ brand_id: string; name: string }>(ENDPOINT_BRANDS, { name }, "brand-create");
      setNewBrandName("");
      await loadBrands();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="space-y-4">
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
          {error}
        </div>
      ) : null}

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
                onClick={() => onSelectBrand(b.brand_id)}
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
                onClick={() => onSelectProject(p.project_id)}
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

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Threads</h2>
        <div className="mt-3 space-y-1">
          {threads.length ? (
            threads.map((t) => (
              <button
                key={t.thread_id}
                type="button"
                onClick={() => onSelectThread(t.thread_id)}
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
      </section>
    </div>
  );
}

