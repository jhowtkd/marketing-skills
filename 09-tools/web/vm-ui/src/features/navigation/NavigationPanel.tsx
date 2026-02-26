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

  const selectedBrand = brands.find((brand) => brand.brand_id === activeBrandId) ?? null;
  const selectedProject = projects.find((project) => project.project_id === activeProjectId) ?? null;
  const selectedThread = threads.find((thread) => thread.thread_id === activeThreadId) ?? null;
  const activeModes = selectedThread?.modes ?? [];
  const hasActiveThread = Boolean(selectedThread);

  return (
    <div className="space-y-4 pb-4">
      {error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
          {error}
        </div>
      ) : null}

      <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">
              Contexto do Job
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Selecione cliente, campanha e job com leitura enxuta. Edicao e cadastro continuam disponiveis, mas
              saem do foco principal.
            </p>
          </div>
          <span className="rounded-full bg-[var(--vm-warm)] px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary-strong)]">
            Rail reduzido
          </span>
        </div>

        <div className="mt-4 grid gap-3">
          <section className="rounded-2xl border border-slate-200 bg-[var(--vm-warm)]/45 p-3">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Cliente</p>
            <p className="mt-2 text-base font-semibold text-slate-900">{selectedBrand?.name ?? "Nenhum cliente selecionado"}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {brands.length ? (
                brands.map((brand) => (
                  <button
                    key={brand.brand_id}
                    type="button"
                    onClick={() => onSelectBrand(brand.brand_id)}
                    className={[
                      "rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-200",
                      brand.brand_id === activeBrandId
                        ? "border-[var(--vm-primary)] bg-[var(--vm-primary)] text-white shadow-sm ring-1 ring-[color:var(--vm-primary)]/15"
                        : "border-slate-200 bg-white text-slate-700 hover:-translate-y-0.5 hover:border-slate-300",
                    ].join(" ")}
                  >
                    {brand.name}
                    {devMode ? <span className="ml-2 text-[11px] text-inherit/80">{brand.brand_id}</span> : null}
                  </button>
                ))
              ) : (
                <p className="text-xs text-slate-500">Sem clientes cadastrados.</p>
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-3">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Campanha</p>
            <p className="mt-2 text-base font-semibold text-slate-900">
              {selectedProject?.name ?? (activeBrandId ? "Escolha uma campanha" : "Selecione um cliente primeiro")}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {projects.length ? (
                projects.map((project) => (
                  <button
                    key={project.project_id}
                    type="button"
                    onClick={() => onSelectProject(project.project_id)}
                    className={[
                      "rounded-full border px-3 py-1.5 text-xs font-medium transition-all duration-200",
                      project.project_id === activeProjectId
                        ? "border-[var(--vm-primary)] bg-[var(--vm-primary)] text-white shadow-sm ring-1 ring-[color:var(--vm-primary)]/15"
                        : "border-slate-200 bg-white text-slate-700 hover:-translate-y-0.5 hover:border-slate-300",
                    ].join(" ")}
                  >
                    {project.name}
                    {devMode ? <span className="ml-2 text-[11px] text-inherit/80">{project.project_id}</span> : null}
                  </button>
                ))
              ) : (
                <p className="text-xs text-slate-500">
                  {activeBrandId ? "Sem campanhas para este cliente." : "Selecione um cliente para listar campanhas."}
                </p>
              )}
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-3">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Job</p>
            <p className="mt-2 text-base font-semibold text-slate-900">
              {selectedThread?.title ?? (activeProjectId ? "Escolha um job" : "Selecione uma campanha primeiro")}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {threads.length ? (
                threads.map((thread) => (
                  <button
                    key={thread.thread_id}
                    type="button"
                    onClick={() => onSelectThread(thread.thread_id)}
                    className={[
                      "rounded-2xl border px-3 py-2 text-left text-xs font-medium transition-all duration-200",
                      thread.thread_id === activeThreadId
                        ? "border-[var(--vm-primary)] bg-[var(--vm-primary)] text-white shadow-sm ring-1 ring-[color:var(--vm-primary)]/15"
                        : "border-slate-200 bg-white text-slate-700 hover:-translate-y-0.5 hover:border-slate-300",
                    ].join(" ")}
                  >
                    <span className="block">{thread.title}</span>
                    {devMode ? <span className="mt-1 block text-[11px] text-inherit/80">{thread.thread_id}</span> : null}
                  </button>
                ))
              ) : (
                <p className="text-xs text-slate-500">
                  {activeProjectId ? "Sem jobs para esta campanha." : "Selecione uma campanha para listar jobs."}
                </p>
              )}
            </div>
          </section>
        </div>

        <details className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50/80 p-3">
          <summary className="cursor-pointer list-none text-sm font-semibold text-slate-700">
            Gerenciar cadastro
          </summary>
          <div className="mt-4 space-y-4">
            <section className="rounded-2xl border border-slate-200 bg-white p-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-slate-900">Clientes</h3>
                <span className="text-xs uppercase tracking-[0.16em] text-slate-400">Secundario</span>
              </div>
              <form onSubmit={handleCreateBrand} className="mt-3 flex gap-2">
                <input
                  value={newBrandName}
                  onChange={(e) => setNewBrandName(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  placeholder="Novo cliente"
                />
                <button type="submit" className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white">
                  Criar
                </button>
              </form>
              <div className="mt-3 space-y-2">
                {brands.length ? (
                  brands.map((brand) => (
                    <div key={brand.brand_id} className="group flex flex-col gap-1">
                      {editingBrandId === brand.brand_id ? (
                        <form onSubmit={(e) => handleEditBrandSubmit(brand.brand_id, e)} className="flex gap-2 w-full">
                          <input
                            autoFocus
                            value={editBrandName}
                            onChange={(e) => setEditBrandName(e.target.value)}
                            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                          />
                          <button type="submit" className="rounded-lg bg-green-600 px-3 py-2 text-sm text-white">
                            Salvar
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingBrandId(null)}
                            className="rounded-lg bg-slate-200 px-3 py-2 text-sm"
                          >
                            X
                          </button>
                        </form>
                      ) : (
                        <div className="flex w-full gap-2">
                          <button
                            type="button"
                            onClick={() => onSelectBrand(brand.brand_id)}
                            className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-800 hover:bg-slate-50"
                          >
                            {brand.name}
                            {devMode ? <span className="ml-2 text-xs text-slate-400">{brand.brand_id}</span> : null}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setEditingBrandId(brand.brand_id);
                              setEditBrandName(brand.name);
                            }}
                            className="hidden shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 group-hover:block"
                          >
                            Editar
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-slate-500">Sem clientes ainda.</div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-slate-900">Campanhas</h3>
                <span className="text-xs uppercase tracking-[0.16em] text-slate-400">Secundario</span>
              </div>
              <form onSubmit={handleCreateProject} className="mt-3 flex gap-2">
                <input
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  disabled={!activeBrandId}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50 disabled:text-slate-400"
                  placeholder={activeBrandId ? "Nova campanha" : "Selecione um cliente"}
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
                  projects.map((project) => (
                    <div key={project.project_id} className="group flex flex-col gap-1">
                      {editingProjectId === project.project_id ? (
                        <form
                          onSubmit={(e) => handleEditProjectSubmit(project.project_id, e)}
                          className="flex gap-2 w-full"
                        >
                          <input
                            autoFocus
                            value={editProjectName}
                            onChange={(e) => setEditProjectName(e.target.value)}
                            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                          />
                          <button type="submit" className="rounded-lg bg-green-600 px-3 py-2 text-sm text-white">
                            Salvar
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingProjectId(null)}
                            className="rounded-lg bg-slate-200 px-3 py-2 text-sm"
                          >
                            X
                          </button>
                        </form>
                      ) : (
                        <div className="flex w-full gap-2">
                          <button
                            type="button"
                            onClick={() => onSelectProject(project.project_id)}
                            className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-800 hover:bg-slate-50"
                          >
                            {project.name}
                            {devMode ? <span className="ml-2 text-xs text-slate-400">{project.project_id}</span> : null}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setEditingProjectId(project.project_id);
                              setEditProjectName(project.name);
                            }}
                            className="hidden shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 group-hover:block"
                          >
                            Editar
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-slate-500">
                    {activeBrandId ? "Sem campanhas ainda." : "Selecione um cliente."}
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-slate-900">Jobs</h3>
                <span className="text-xs uppercase tracking-[0.16em] text-slate-400">Secundario</span>
              </div>
              <form onSubmit={handleCreateThread} className="mt-3 flex gap-2">
                <input
                  value={newThreadTitle}
                  onChange={(e) => setNewThreadTitle(e.target.value)}
                  disabled={!activeProjectId}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm disabled:bg-slate-50 disabled:text-slate-400"
                  placeholder={activeProjectId ? "Novo job" : "Selecione uma campanha"}
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
                  threads.map((thread) => (
                    <div key={thread.thread_id} className="group flex flex-col gap-1">
                      {editingThreadId === thread.thread_id ? (
                        <form onSubmit={(e) => handleEditThreadSubmit(thread.thread_id, e)} className="flex gap-2 w-full">
                          <input
                            autoFocus
                            value={editThreadTitle}
                            onChange={(e) => setEditThreadTitle(e.target.value)}
                            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                          />
                          <button type="submit" className="rounded-lg bg-green-600 px-3 py-2 text-sm text-white">
                            Salvar
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingThreadId(null)}
                            className="rounded-lg bg-slate-200 px-3 py-2 text-sm"
                          >
                            X
                          </button>
                        </form>
                      ) : (
                        <div className="flex w-full gap-2">
                          <button
                            type="button"
                            onClick={() => onSelectThread(thread.thread_id)}
                            className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-800 hover:bg-slate-50"
                          >
                            {thread.title}
                            {devMode ? <span className="ml-2 text-xs text-slate-400">{thread.thread_id}</span> : null}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setEditingThreadId(thread.thread_id);
                              setEditThreadTitle(thread.title);
                            }}
                            className="hidden shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 group-hover:block"
                          >
                            Editar
                          </button>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-slate-500">
                    {activeProjectId ? "Sem jobs ainda." : "Selecione uma campanha."}
                  </div>
                )}
              </div>
            </section>
          </div>
        </details>
      </section>

      <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">Modo</h2>
        <p className="mt-2 text-sm text-slate-600">
          Os modos ativos definem o tipo de entrega. Mantenha apenas o necessario para reduzir ru ruido operacional.
        </p>
        {!activeThreadId ? (
          <p className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-sm text-slate-500">
            Selecione um job para configurar os modos desta frente.
          </p>
        ) : (
          <div className="mt-4 space-y-3">
            <div className="flex flex-wrap gap-2">
              {activeModes.length ? (
                activeModes.map((mode) => (
                  <span
                    key={mode}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-[var(--vm-warm)] px-3 py-1.5 text-xs font-medium text-slate-800"
                  >
                    {mode}
                    <button
                      type="button"
                      onClick={() => handleRemoveMode(activeThreadId, mode)}
                      className="text-slate-400 hover:text-red-500"
                      aria-label={`Remover modo ${mode}`}
                    >
                      &times;
                    </button>
                  </span>
                ))
              ) : (
                <p className="text-sm text-slate-500">Nenhum modo ativo neste job.</p>
              )}
            </div>

            <form onSubmit={(e) => handleAddMode(activeThreadId, e)} className="flex gap-2">
              <input
                value={newModeName}
                onChange={(e) => setNewModeName(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="Adicionar modo (ex: content_calendar)"
              />
              <button type="submit" className="rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white">
                Adicionar
              </button>
            </form>
          </div>
        )}
      </section>

      <section className="rounded-[1.5rem] border border-[color:var(--vm-line)] bg-white/90 p-4 shadow-sm">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--vm-primary)]">Versoes</h2>
        <p className="mt-2 text-sm text-slate-600">
          A leitura da versao ativa acontece no canvas central. Use este rail apenas para orientar o fluxo.
        </p>
        <div className="mt-4 grid gap-3">
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/90 p-3">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Leitura principal</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {hasActiveThread
                ? "Canvas editorial desbloqueado para esta frente."
                : "Escolha um job para abrir o canvas deliverable-first."}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Versao ativa</p>
            <p className="mt-2 text-sm font-semibold text-slate-900">
              {selectedThread ? "Selecione ou gere uma versao no canvas central." : "Escolha um job para liberar as versoes."}
            </p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-slate-500">Proximo passo</p>
            <p className="mt-2 text-sm text-slate-700">
              {selectedThread
                ? "Defina o pedido no canvas, gere a versao e acompanhe bloqueios no painel da direita."
                : "Contextualize cliente, campanha e job para comecar o fluxo deliverable-first."}
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
