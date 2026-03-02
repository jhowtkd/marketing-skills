# VM Unified API Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrar vm-unified frontend com vm_webapp backend API, substituindo mock data por chamadas reais.

**Architecture:** API client modular com React Query (ou fetch puro) + hooks customizados para cada recurso (brands, projects, threads, runs). Proxy config para dev, env vars para produção.

**Tech Stack:** React Query (@tanstack/react-query) para caching e estado de servidor, ou fetch puro com Zustand.

---

## Decisão: React Query vs Fetch Puro

**Opção A: React Query (recomendada)**
- Caching automático, refetching, loading/error states
- Melhor UX com stale-while-revalidate
- Devtools para debugging

**Opção B: Fetch Puro + Zustand**
- Menos dependências
- Mais controle manual
- Mais código boilerplate

**Recomendação:** React Query — compensa para a complexidade de hierarquia Brand→Project→Thread→Run.

---

## Task 1: Instalar React Query

**Files:**
- Modify: `vm-unified/package.json`
- Create: `vm-unified/src/lib/query-client.ts`
- Modify: `vm-unified/src/main.tsx`

**Step 1: Instalar dependências**

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-unified
npm install @tanstack/react-query @tanstack/react-query-devtools
```

**Step 2: Criar Query Client**

Create: `vm-unified/src/lib/query-client.ts`

```typescript
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      refetchOnWindowFocus: true,
      retry: 2,
    },
  },
})
```

**Step 3: Adicionar Provider no main.tsx**

Modify: `vm-unified/src/main.tsx`

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import App from './app/App'
import { queryClient } from './lib/query-client'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>,
)
```

**Step 4: Commit**

```bash
cd /Users/jhonatan/Repos/marketing-skills
git add 09-tools/web/vm-unified/
git commit -m "feat(vm-unified): add React Query for API state management"
```

---

## Task 2: API Client Base

**Files:**
- Create: `vm-unified/src/lib/api.ts`

**Step 1: Criar API client base**

Create: `vm-unified/src/lib/api.ts`

```typescript
const API_BASE = '/api/v2'

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message)
    this.name = 'APIError'
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options)
  
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const detail = payload.detail || `Request failed (${response.status})`
    throw new APIError(detail, response.status, detail)
  }

  return response.json() as T
}

export async function get<T>(path: string): Promise<T> {
  return fetchJson<T>(`${API_BASE}${path}`)
}

export async function post<T>(path: string, payload: unknown, idempotencyKey?: string): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey
  }

  return fetchJson<T>(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  })
}

export function buildIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/lib/api.ts
git commit -m "feat(vm-unified): add API client base with error handling"
```

---

## Task 3: Hooks de API - Brands

**Files:**
- Create: `vm-unified/src/hooks/use-brands.ts`

**Step 1: Criar hook useBrands**

Create: `vm-unified/src/hooks/use-brands.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, buildIdempotencyKey } from '@/lib/api'
import type { Brand } from '@/types'

const BRANDS_KEY = 'brands'

interface BrandResponse {
  brand_id: string
  name: string
}

interface BrandsResponse {
  brands: BrandResponse[]
}

function mapBrand(response: BrandResponse): Brand {
  return {
    id: response.brand_id,
    name: response.name,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
}

export function useBrands() {
  return useQuery({
    queryKey: [BRANDS_KEY],
    queryFn: async () => {
      const response = await get<BrandsResponse>('/brands')
      return response.brands.map(mapBrand)
    },
  })
}

export function useCreateBrand() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (name: string) => {
      const brandId = `brand-${Date.now().toString(36)}`
      await post('/brands', {
        brand_id: brandId,
        name,
      }, buildIdempotencyKey('brand-create'))
      return brandId
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [BRANDS_KEY] })
    },
  })
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/use-brands.ts
git commit -m "feat(vm-unified): add useBrands hook with React Query"
```

---

## Task 4: Hooks de API - Projects

**Files:**
- Create: `vm-unified/src/hooks/use-projects.ts`

**Step 1: Criar hook useProjects**

Create: `vm-unified/src/hooks/use-projects.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, buildIdempotencyKey } from '@/lib/api'
import type { Project } from '@/types'

const PROJECTS_KEY = 'projects'

interface ProjectResponse {
  project_id: string
  brand_id: string
  name: string
}

interface ProjectsResponse {
  projects: ProjectResponse[]
}

function mapProject(response: ProjectResponse): Project {
  return {
    id: response.project_id,
    brandId: response.brand_id,
    name: response.name,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
}

export function useProjects(brandId: string | null) {
  return useQuery({
    queryKey: [PROJECTS_KEY, brandId],
    queryFn: async () => {
      if (!brandId) return []
      const response = await get<ProjectsResponse>(`/projects?brand_id=${encodeURIComponent(brandId)}`)
      return response.projects.map(mapProject)
    },
    enabled: !!brandId,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ brandId, name }: { brandId: string; name: string }) => {
      const projectId = `proj-${Date.now().toString(36)}`
      await post('/projects', {
        project_id: projectId,
        brand_id: brandId,
        name,
        objective: '',
        channels: [],
      }, buildIdempotencyKey('project-create'))
      return projectId
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [PROJECTS_KEY, variables.brandId] })
    },
  })
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/use-projects.ts
git commit -m "feat(vm-unified): add useProjects hook"
```

---

## Task 5: Hooks de API - Threads

**Files:**
- Create: `vm-unified/src/hooks/use-threads.ts`

**Step 1: Criar hook useThreads**

Create: `vm-unified/src/hooks/use-threads.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, buildIdempotencyKey } from '@/lib/api'
import type { Thread } from '@/types'

const THREADS_KEY = 'threads'

interface ThreadResponse {
  thread_id: string
  project_id: string
  title: string
}

interface ThreadsResponse {
  threads: ThreadResponse[]
}

function mapThread(response: ThreadResponse): Thread {
  return {
    id: response.thread_id,
    projectId: response.project_id,
    name: response.title,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
}

export function useThreads(projectId: string | null) {
  return useQuery({
    queryKey: [THREADS_KEY, projectId],
    queryFn: async () => {
      if (!projectId) return []
      const response = await get<ThreadsResponse>(`/threads?project_id=${encodeURIComponent(projectId)}`)
      return response.threads.map(mapThread)
    },
    enabled: !!projectId,
  })
}

export function useCreateThread() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ 
      brandId, 
      projectId, 
      title 
    }: { 
      brandId: string
      projectId: string
      title: string 
    }) => {
      const threadId = `thread-${Date.now().toString(36)}`
      await post('/threads', {
        thread_id: threadId,
        project_id: projectId,
        brand_id: brandId,
        title,
      }, buildIdempotencyKey('thread-create'))
      return threadId
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [THREADS_KEY, variables.projectId] })
    },
  })
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/use-threads.ts
git commit -m "feat(vm-unified): add useThreads hook"
```

---

## Task 6: Hooks de API - Runs

**Files:**
- Create: `vm-unified/src/hooks/use-runs.ts`

**Step 1: Criar hook useRuns**

Create: `vm-unified/src/hooks/use-runs.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, buildIdempotencyKey } from '@/lib/api'
import type { Run, Stage } from '@/types'

const RUNS_KEY = 'runs'

interface StageResponse {
  key: string
  name: string
  status: string
}

interface RunResponse {
  run_id: string
  thread_id: string
  status: string
  current_stage?: string
  stages?: StageResponse[]
  created_at?: string
  updated_at?: string
}

interface RunsResponse {
  runs: RunResponse[]
}

function mapStage(response: StageResponse): Stage {
  return {
    key: response.key,
    name: response.name,
    status: response.status as Stage['status'],
  }
}

function mapRun(response: RunResponse): Run {
  return {
    id: response.run_id,
    threadId: response.thread_id,
    status: response.status as Run['status'],
    currentStage: response.current_stage || null,
    stages: response.stages?.map(mapStage) || [],
    createdAt: response.created_at || new Date().toISOString(),
    updatedAt: response.updated_at || new Date().toISOString(),
  }
}

export function useRuns(threadId: string | null) {
  return useQuery({
    queryKey: [RUNS_KEY, threadId],
    queryFn: async () => {
      if (!threadId) return []
      const response = await get<RunsResponse>(`/threads/${encodeURIComponent(threadId)}/workflow-runs`)
      return response.runs.map(mapRun)
    },
    enabled: !!threadId,
    refetchInterval: (data) => {
      // Refetch more frequently if there's a running run
      const hasRunning = data?.some(run => 
        run.status === 'running' || run.status === 'queued'
      )
      return hasRunning ? 2000 : false
    },
  })
}

export function useCreateRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      threadId,
      mode,
      requestText,
    }: {
      threadId: string
      mode: string
      requestText: string
    }) => {
      const response = await post<{ run_id: string; status: string }>(
        `/threads/${encodeURIComponent(threadId)}/workflow-runs`,
        {
          mode,
          request_text: requestText,
          skill_overrides: {},
        },
        buildIdempotencyKey('workflow-run')
      )
      return response.run_id
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [RUNS_KEY, variables.threadId] })
    },
  })
}

export function useResumeRun() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (runId: string) => {
      const response = await post<{ run_id: string; status: string }>(
        `/workflow-runs/${encodeURIComponent(runId)}/resume`,
        {},
        buildIdempotencyKey(`run-resume-${runId}`)
      )
      return response
    },
    onSuccess: () => {
      // Invalidate all runs since we don't know the threadId here
      queryClient.invalidateQueries({ queryKey: [RUNS_KEY] })
    },
  })
}

export function useGrantApproval() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (approvalId: string) => {
      await post(
        `/approvals/${encodeURIComponent(approvalId)}/grant`,
        {},
        buildIdempotencyKey(`approval-grant-${approvalId}`)
      )
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [RUNS_KEY] })
    },
  })
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/use-runs.ts
git commit -m "feat(vm-unified): add useRuns hook with polling"
```

---

## Task 7: Integrar Hooks na Navigation Panel

**Files:**
- Modify: `vm-unified/src/components/layout/navigation-panel.tsx`

**Step 1: Atualizar NavigationPanel para usar hooks reais**

Modify: `vm-unified/src/components/layout/navigation-panel.tsx`

```typescript
import { ChevronDown, ChevronRight, Plus, MoreHorizontal, Loader2 } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { useBrands } from '@/hooks/use-brands'
import { useProjects } from '@/hooks/use-projects'
import { useThreads } from '@/hooks/use-threads'
import { cn } from '@/lib/utils'

export function NavigationPanel() {
  const {
    activeBrandId,
    activeProjectId,
    activeThreadId,
    selectBrand,
    selectProject,
    selectThread,
  } = useStore()

  const { data: brands = [], isLoading: isLoadingBrands } = useBrands()
  const { data: projects = [], isLoading: isLoadingProjects } = useProjects(activeBrandId)
  const { data: threads = [], isLoading: isLoadingThreads } = useThreads(activeProjectId)

  const getBrandProjects = (brandId: string) =>
    projects.filter(p => p.brandId === brandId)

  const getProjectThreads = (projectId: string) =>
    threads.filter(t => t.projectId === projectId)

  if (isLoadingBrands) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-vm-ink-muted" />
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-medium text-vm-ink-subtle uppercase tracking-wider">
          Brands
        </span>
      </div>

      <div className="space-y-1">
        {brands.map((brand) => {
          const isActive = brand.id === activeBrandId
          const brandProjects = getBrandProjects(brand.id)

          return (
            <div key={brand.id} className="group">
              <button
                onClick={() => selectBrand(isActive ? null : brand.id)}
                className={cn(
                  'w-full flex items-center gap-2 px-2 py-1.5 rounded-vm-md transition-colors',
                  isActive ? 'bg-vm-primary-dim text-vm-primary' : 'hover:bg-vm-hover'
                )}
              >
                {isActive ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5 text-vm-ink-muted" />
                )}
                <span className="text-sm font-medium flex-1 text-left">{brand.name}</span>
                <button
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-vm-hover rounded transition-opacity"
                  onClick={(e) => e.stopPropagation()}
                >
                  <MoreHorizontal className="w-3.5 h-3.5" />
                </button>
              </button>

              {isActive && (
                <div className="ml-4 mt-0.5 space-y-0.5 border-l border-vm-border pl-2">
                  {isLoadingProjects ? (
                    <div className="px-2 py-1.5">
                      <Loader2 className="w-4 h-4 animate-spin text-vm-ink-muted" />
                    </div>
                  ) : (
                    brandProjects.map((project) => {
                      const isProjectActive = project.id === activeProjectId
                      const projectThreads = getProjectThreads(project.id)

                      return (
                        <div key={project.id}>
                          <button
                            onClick={() => selectProject(isProjectActive ? null : project.id)}
                            className={cn(
                              'w-full flex items-center gap-2 px-2 py-1.5 rounded-vm-md transition-colors',
                              isProjectActive ? 'text-vm-ink' : 'text-vm-ink-muted hover:text-vm-ink hover:bg-vm-hover'
                            )}
                          >
                            {isProjectActive ? (
                              <ChevronDown className="w-3.5 h-3.5" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5" />
                            )}
                            <span className="text-sm">{project.name}</span>
                          </button>

                          {isProjectActive && (
                            <div className="ml-4 mt-0.5 space-y-0.5">
                              {isLoadingThreads ? (
                                <div className="px-2 py-1.5">
                                  <Loader2 className="w-3 h-3 animate-spin text-vm-ink-muted" />
                                </div>
                              ) : (
                                projectThreads.map((thread) => {
                                  const isThreadActive = thread.id === activeThreadId
                                  return (
                                    <button
                                      key={thread.id}
                                      onClick={() => selectThread(thread.id)}
                                      className={cn(
                                        'w-full text-left px-2 py-1.5 rounded-vm-md text-sm transition-colors',
                                        isThreadActive
                                          ? 'bg-vm-primary-dim text-vm-primary'
                                          : 'text-vm-ink-muted hover:bg-vm-hover'
                                      )}
                                    >
                                      {thread.name}
                                    </button>
                                  )
                                })
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <button className="mt-4 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-vm-md border border-dashed border-vm-border text-sm text-vm-ink-muted hover:border-vm-primary hover:text-vm-primary transition-colors">
        <Plus className="w-4 h-4" />
        New Brand
      </button>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/components/layout/navigation-panel.tsx
git commit -m "feat(vm-unified): integrate API hooks into NavigationPanel"
```

---

## Task 8: Integrar Runs no Command Rail

**Files:**
- Modify: `vm-unified/src/components/layout/command-rail.tsx`

**Step 1: Atualizar CommandRail para usar hooks reais**

Modify: `vm-unified/src/components/layout/command-rail.tsx`

```typescript
import { Command, Play, CheckCircle, RotateCcw, FileText, Loader2 } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { useRuns, useResumeRun } from '@/hooks/use-runs'
import { Kbd } from '@/components/ui/kbd'
import { cn } from '@/lib/utils'

export function CommandRail() {
  const { activeThreadId, activeRunId } = useStore()
  const { data: runs = [], isLoading } = useRuns(activeThreadId)
  const activeRun = runs.find(r => r.id === activeRunId)
  const resumeRun = useResumeRun()

  return (
    <div className="h-full flex flex-col bg-vm-surface border-l border-vm-border">
      {/* Command Input */}
      <div className="p-3 border-b border-vm-border">
        <div className="flex items-center gap-2 px-3 py-2 rounded-vm-md bg-vm-bg border border-vm-border">
          <Command className="w-4 h-4 text-vm-ink-muted" />
          <input
            type="text"
            placeholder="Type a command..."
            className="flex-1 bg-transparent text-sm text-vm-ink placeholder:text-vm-ink-subtle outline-none"
          />
          <Kbd>⌘K</Kbd>
        </div>
      </div>

      {/* Actions */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-vm-ink-muted" />
          </div>
        ) : activeRun ? (
          <>
            <Section title="Run Actions">
              <CommandItem 
                icon={Play} 
                label="Resume Workflow" 
                shortcut="⌘R"
                onClick={() => resumeRun.mutate(activeRun.id)}
                isLoading={resumeRun.isPending}
              />
              <CommandItem icon={CheckCircle} label="Approve Stage" shortcut="⌘A" />
              <CommandItem icon={RotateCcw} label="Retry Stage" />
            </Section>

            <Section title="Stage Status">
              {activeRun.stages?.map((stage) => (
                <div
                  key={stage.key}
                  className="flex items-center gap-2 px-2 py-1.5 text-sm"
                >
                  <StatusDot status={stage.status} />
                  <span className="text-vm-ink-muted">{stage.name}</span>
                </div>
              ))}
            </Section>
          </>
        ) : (
          <div className="px-2 py-8 text-center">
            <p className="text-sm text-vm-ink-subtle">No active run</p>
            <p className="text-xs text-vm-ink-subtle mt-1">
              Select a thread to view actions
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <div className="px-2 py-1.5 text-xs font-medium text-vm-ink-subtle uppercase tracking-wider">
        {title}
      </div>
      <div className="mt-1 space-y-0.5">{children}</div>
    </div>
  )
}

function CommandItem({
  icon: Icon,
  label,
  shortcut,
  onClick,
  isLoading,
}: {
  icon: React.ElementType
  label: string
  shortcut?: string
  onClick?: () => void
  isLoading?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={isLoading}
      className={cn(
        'w-full flex items-center gap-3 px-2 py-1.5 rounded-vm-md transition-colors group',
        'hover:bg-vm-hover text-left disabled:opacity-50 disabled:cursor-not-allowed'
      )}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 text-vm-ink-muted animate-spin" />
      ) : (
        <Icon className="w-4 h-4 text-vm-ink-muted" />
      )}
      <span className="text-sm text-vm-ink">{label}</span>
      {shortcut && (
        <span className="ml-auto text-xs text-vm-ink-subtle opacity-0 group-hover:opacity-100 transition-opacity">
          {shortcut}
        </span>
      )}
    </button>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors = {
    pending: 'bg-vm-ink-subtle',
    running: 'bg-vm-primary animate-pulse',
    waiting_approval: 'bg-vm-warning',
    completed: 'bg-vm-success',
    failed: 'bg-vm-error',
    skipped: 'bg-vm-ink-subtle',
  }
  return <div className={cn('w-2 h-2 rounded-full', colors[status] || colors.pending)} />
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/components/layout/command-rail.tsx
git commit -m "feat(vm-unified): integrate useRuns hook into CommandRail"
```

---

## Task 9: Testar Integração

**Step 1: Subir backend e frontend**

Terminal 1 (backend):
```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools
uv run python -m vm_webapp serve --host 127.0.0.1 --port 8766
```

Terminal 2 (frontend):
```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-unified
npm run dev
```

**Step 2: Verificar se dados carregam**

Abrir http://localhost:5173 e verificar:
- [ ] Brands aparecem na navegação
- [ ] Expandir brand carrega projects
- [ ] Expandir project carrega threads
- [ ] Selecionar thread carrega runs no command rail

**Step 3: Commit final**

```bash
git commit --allow-empty -m "test(vm-unified): verify API integration"
```

---

## Resumo

Este plano integra vm-unified com vm_webapp API:

1. **React Query** para estado de servidor
2. **API client base** com error handling
3. **Hooks específicos** para cada recurso (brands, projects, threads, runs)
4. **NavigationPanel** integrado com loading states
5. **CommandRail** com runs reais e polling
6. **Teste completo** contra backend

**Próximos passos:**
- Implementar criação de brands/projects/threads (modal + forms)
- Implementar workflow run creation
- Implementar artifact viewing
- Error boundaries e retry logic
