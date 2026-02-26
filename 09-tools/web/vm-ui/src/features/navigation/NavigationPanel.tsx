import { useEffect, useState, type FormEvent } from "react";

import { fetchJson, postJson, patchJson } from "../../api/client";
import { ENDPOINT_BRANDS, ENDPOINT_PROJECTS, ENDPOINT_THREADS } from "../../api/endpoints";
import type { Brand, BrandsResponse, Project, ProjectsResponse, Thread, ThreadsResponse } from "../../api/types";

type MaybeId = string | null;

type Props = {
  activeBrandId: MaybeId;
  activeProjectId: MaybeId;
  activeThreadId: MaybeId;
  devMode: boolean;
  onSelectBrand: (brandId: MaybeId) => void;
  onSelectProject: (projectId: MaybeId) => void;
  onSelectThread: (threadId: MaybeId) => void;
};

export default function NavigationPanel({
  activeBrandId,
  activeProjectId,
  activeThreadId,
  devMode,
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

  // BRANDS ACTIONS
  const [newBrandName, setNewBrandName] = useState("");
  const [editingBrandId, setEditingBrandId] = useState<string | null>(null);
  const [editBrandName, setEditBrandName] = useState("");

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

  async function handleEditBrandSubmit(brandId: string, event: FormEvent) {
    event.preventDefault();
    const name = editBrandName.trim();
    if (!name) return;
    try {
      setError(null);
      await patchJson(`${ENDPOINT_BRANDS}/${brandId}`, { name }, "brand-edit");
      setEditingBrandId(null);
      await loadBrands();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  // PROJECTS ACTIONS
  const [newProjectName, setNewProjectName] = useState("");
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [editProjectName, setEditProjectName] = useState("");

  async function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newProjectName.trim();
    if (!name || !activeBrandId) return;
    try {
      setError(null);
      await postJson(ENDPOINT_PROJECTS, { name, brand_id: activeBrandId }, "project-create");
      setNewProjectName("");
      await loadProjects(activeBrandId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleEditProjectSubmit(projectId: string, event: FormEvent) {
    event.preventDefault();
    const name = editProjectName.trim();
    if (!name || !activeBrandId) return;
    try {
      setError(null);
      const p = projects.find((x) => x.project_id === projectId);
      await patchJson(`${ENDPOINT_PROJECTS}/${projectId}`, { 
        name,
        objective: p?.objective || "",
        channels: p?.channels || []
      }, "project-edit");
      setEditingProjectId(null);
      await loadProjects(activeBrandId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  // THREADS ACTIONS
  const [newThreadTitle, setNewThreadTitle] = useState("");
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null);
  const [editThreadTitle, setEditThreadTitle] = useState("");

  async function handleCreateThread(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const title = newThreadTitle.trim();
    if (!title || !activeBrandId || !activeProjectId) return;
    try {
      setError(null);
      await postJson(ENDPOINT_THREADS, { title, brand_id: activeBrandId, project_id: activeProjectId }, "thread-create");
      setNewThreadTitle("");
      await loadThreads(activeProjectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleEditThreadSubmit(threadId: string, event: FormEvent) {
    event.preventDefault();
    const title = editThreadTitle.trim();
    if (!title || !activeProjectId) return;
    try {
      setError(null);
      await patchJson(`${ENDPOINT_THREADS}/${threadId}`, { title }, "thread-edit");
      setEditingThreadId(null);
      await loadThreads(activeProjectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  // MODES ACTIONS
  const [newModeName, setNewModeName] = useState("");

  async function handleAddMode(threadId: string, event: FormEvent) {
    event.preventDefault();
    const mode = newModeName.trim();
    if (!mode || !activeProjectId) return;
    try {
      setError(null);
      await postJson(`${ENDPOINT_THREADS}/${threadId}/modes`, { mode }, "mode-add");
      setNewModeName("");
      await loadThreads(activeProjectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleRemoveMode(threadId: string, mode: string) {
    if (!activeProjectId) return;
    try {
      setError(null);
      await postJson(`${ENDPOINT_THREADS}/${threadId}/modes/${encodeURIComponent(mode)}/remove`, {}, "mode-remove");
      await loadThreads(activeProjectId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="space-y-4 pb-8">
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
          {error}
        </div>
      ) : null}

      {/* MARCAS SECTION */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900 mb-3">Marcas</h2>
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
        <div className="mt-3 space-y-2">
          {brands.length ? (
            brands.map((b) => (
              <div key={b.brand_id} className="group flex flex-col gap-1">
                {editingBrandId === b.brand_id ? (
                  <form onSubmit={(e) => handleEditBrandSubmit(b.brand_id, e)} className="flex gap-2 w-full">
                    <input
                      autoFocus
                      value={editBrandName}
                      onChange={(e) => setEditBrandName(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                    />
                    <button type="submit" className="rounded-lg bg-green-600 px-3 py-2 text-sm text-white">Salvar</button>
                    <button type="button" onClick={() => setEditingBrandId(null)} className="rounded-lg bg-slate-200 px-3 py-2 text-sm">X</button>
                  </form>
                ) : (
                  <div className="flex w-full gap-2">
                    <button
                      type="button"
                      onClick={() => onSelectBrand(b.brand_id)}
                      className={[
                        "flex-1 rounded-lg border px-3 py-2 text-left text-sm",
                        b.brand_id === activeBrandId
                          ? "border-blue-200 bg-blue-50 text-blue-900"
                          : "border-slate-200 bg-white text-slate-800 hover:bg-slate-50",
                      ].join(" ")}
                    >
                      {b.name}
                      {devMode ? <span className="ml-2 text-xs text-slate-400">{b.brand_id}</span> : null}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingBrandId(b.brand_id);
                        setEditBrandName(b.name);
                      }}
                      className="hidden group-hover:block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 shrink-0"
                    >
                      Editar
                    </button>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="text-sm text-slate-500">Sem marcas ainda.</div>
          )}
        </div>
      </section>

      {/* PROJETOS SECTION */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900 mb-3">Projetos</h2>
        <form onSubmit={handleCreateProject} className="flex gap-2">
          <input
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            disabled={!activeBrandId}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50 disabled:text-slate-400"
            placeholder={activeBrandId ? "Novo projeto" : "Selecione uma marca"}
          />
          <button
            type="submit"
            disabled={!activeBrandId}
            className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Criar
          </button>
        </form>
        <div className="mt-3 space-y-2">
          {projects.length ? (
            projects.map((p) => (
              <div key={p.project_id} className="group flex flex-col gap-1">
                {editingProjectId === p.project_id ? (
                  <form onSubmit={(e) => handleEditProjectSubmit(p.project_id, e)} className="flex gap-2 w-full">
                    <input
                      autoFocus
                      value={editProjectName}
                      onChange={(e) => setEditProjectName(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                    />
                    <button type="submit" className="rounded-lg bg-green-600 px-3 py-2 text-sm text-white">Salvar</button>
                    <button type="button" onClick={() => setEditingProjectId(null)} className="rounded-lg bg-slate-200 px-3 py-2 text-sm">X</button>
                  </form>
                ) : (
                  <div className="flex w-full gap-2">
                    <button
                      type="button"
                      onClick={() => onSelectProject(p.project_id)}
                      className={[
                        "flex-1 rounded-lg border px-3 py-2 text-left text-sm",
                        p.project_id === activeProjectId
                          ? "border-blue-200 bg-blue-50 text-blue-900"
                          : "border-slate-200 bg-white text-slate-800 hover:bg-slate-50",
                      ].join(" ")}
                    >
                      {p.name}
                      {devMode ? <span className="ml-2 text-xs text-slate-400">{p.project_id}</span> : null}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingProjectId(p.project_id);
                        setEditProjectName(p.name);
                      }}
                      className="hidden group-hover:block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 shrink-0"
                    >
                      Editar
                    </button>
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="text-sm text-slate-500">
              {activeBrandId ? "Sem projetos ainda." : "Selecione uma marca."}
            </div>
          )}
        </div>
      </section>

      {/* THREADS SECTION */}
      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900 mb-3">Threads</h2>
        <form onSubmit={handleCreateThread} className="flex gap-2">
          <input
            value={newThreadTitle}
            onChange={(e) => setNewThreadTitle(e.target.value)}
            disabled={!activeProjectId}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50 disabled:text-slate-400"
            placeholder={activeProjectId ? "Nova thread" : "Selecione um projeto"}
          />
          <button
            type="submit"
            disabled={!activeProjectId}
            className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Criar
          </button>
        </form>
        <div className="mt-3 space-y-2">
          {threads.length ? (
            threads.map((t) => (
              <div key={t.thread_id} className="group flex flex-col gap-1">
                {editingThreadId === t.thread_id ? (
                  <form onSubmit={(e) => handleEditThreadSubmit(t.thread_id, e)} className="flex gap-2 w-full">
                    <input
                      autoFocus
                      value={editThreadTitle}
                      onChange={(e) => setEditThreadTitle(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                    />
                    <button type="submit" className="rounded-lg bg-green-600 px-3 py-2 text-sm text-white">Salvar</button>
                    <button type="button" onClick={() => setEditingThreadId(null)} className="rounded-lg bg-slate-200 px-3 py-2 text-sm">X</button>
                  </form>
                ) : (
                  <div className="flex flex-col w-full gap-2">
                    <div className="flex w-full gap-2">
                      <button
                        type="button"
                        onClick={() => onSelectThread(t.thread_id)}
                        className={[
                          "flex-1 rounded-lg border px-3 py-2 text-left text-sm",
                          t.thread_id === activeThreadId
                            ? "border-blue-200 bg-blue-50 text-blue-900"
                            : "border-slate-200 bg-white text-slate-800 hover:bg-slate-50",
                        ].join(" ")}
                    >
                      {t.title}
                      {devMode ? <span className="ml-2 text-xs text-slate-400">{t.thread_id}</span> : null}
                    </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingThreadId(t.thread_id);
                          setEditThreadTitle(t.title);
                        }}
                        className="hidden group-hover:block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 shrink-0"
                      >
                        Editar
                      </button>
                    </div>

                    {/* MODES LIST FOR ACTIVE THREAD */}
                    {t.thread_id === activeThreadId && (
                      <div className="ml-4 pl-4 border-l-2 border-slate-200 mt-1 mb-2 flex flex-col gap-2">
                        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Modes</div>
                        {t.modes && t.modes.length > 0 ? (
                          <div className="flex flex-wrap gap-2">
                            {t.modes.map((mode) => (
                              <span
                                key={mode}
                                className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
                              >
                                {mode}
                                <button
                                  type="button"
                                  onClick={() => handleRemoveMode(t.thread_id, mode)}
                                  className="text-slate-400 hover:text-red-500 focus:outline-none"
                                >
                                  &times;
                                </button>
                              </span>
                            ))}
                          </div>
                        ) : (
                          <div className="text-xs text-slate-400">Nenhum mode ativo.</div>
                        )}
                        <form onSubmit={(e) => handleAddMode(t.thread_id, e)} className="flex gap-2 mt-1">
                          <input
                            value={newModeName}
                            onChange={(e) => setNewModeName(e.target.value)}
                            className="w-full rounded border border-slate-200 px-2 py-1 text-xs"
                            placeholder="Add mode (ex: plan_90d)"
                          />
                          <button
                            type="submit"
                            className="rounded bg-slate-200 px-3 py-1 text-xs font-medium hover:bg-slate-300 transition-colors"
                          >
                            Add
                          </button>
                        </form>
                      </div>
                    )}
                  </div>
                )}
              </div>
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
