# VM Unified API Integration Design

> Integração do vm-unified frontend com vm_webapp backend API usando Adapter Pattern e React Query.

---

## 1. Overview

### 1.1 Contexto
- **Frontend:** vm-unified (React + TypeScript + Tailwind) — layout 3 colunas pronto
- **Backend:** vm_webapp (FastAPI) — API completa em `/api/v2/*`
- **Desafio:** Backend usa snake_case (`brand_id`), frontend usa camelCase (`id`)

### 1.2 Solução
**Adapter Pattern Híbrido:**
- Types exatos do backend em `types/api.ts` (snake_case)
- Types limpos para UI em `types/index.ts` (camelCase)
- Adapters fazem conversão bidirecional
- React Query para estado de servidor, Zustand para estado de UI

### 1.3 Restrição Crítica
**ZERO mudanças no backend.** Toda adaptação acontece no frontend.

---

## 2. Arquitetura

### 2.1 Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Backend ──→ API Client ──→ React Query ──→ Adapter ──→ Component  │
│  (snake)      (raw)          (cached)       (map)       (camel)     │
│                                                                     │
│  Component ──→ Adapter ──→ API Client ──→ Backend                  │
│  (camel)       (unmap)     (fetch)        (snake)                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Estrutura de Arquivos

```
src/
├── types/
│   ├── api.ts              # Exatas do backend (snake_case)
│   └── index.ts            # Limpas para UI (camelCase)
│
├── adapters/
│   ├── brand-adapter.ts    # BrandResponse ↔ Brand
│   ├── project-adapter.ts  # ProjectResponse ↔ Project
│   ├── thread-adapter.ts   # ThreadResponse ↔ Thread
│   └── run-adapter.ts      # RunResponse ↔ Run
│
├── hooks/api/              # React Query hooks
│   ├── use-brands.ts       # GET, POST, PATCH, DELETE
│   ├── use-projects.ts
│   ├── use-threads.ts
│   └── use-runs.ts
│
├── hooks/ui/               # Zustand + UI hooks
│   ├── use-store.ts        # Estado de UI (seleção, modo)
│   └── use-toast.ts        # Notificações globais
│
├── lib/
│   ├── api.ts              # Cliente HTTP base
│   └── query-client.ts     # Config React Query
│
└── components/             # Usam types/index.ts (limpo)
```

---

## 3. Type Definitions

### 3.1 Backend Types (`types/api.ts`)

Exatos do contrato da API, snake_case.

```typescript
// Brand
export interface BrandResponse {
  brand_id: string;
  name: string;
}

export interface BrandsResponse {
  brands: BrandResponse[];
}

// Project
export interface ProjectResponse {
  project_id: string;
  brand_id: string;
  name: string;
  objective?: string;
  channels?: string[];
  due_date?: string;
}

export interface ProjectsResponse {
  projects: ProjectResponse[];
}

// Thread
export interface ThreadResponse {
  thread_id: string;
  project_id: string;
  brand_id: string;
  title: string;
  status: string;
  modes?: string[];
  last_activity_at?: string;
}

export interface ThreadsResponse {
  threads: ThreadResponse[];
}

// Run
export interface StageResponse {
  key: string;
  name: string;
  status: string;
}

export interface RunResponse {
  run_id: string;
  thread_id: string;
  status: string;
  current_stage?: string;
  stages?: StageResponse[];
  created_at?: string;
  updated_at?: string;
}

export interface RunsResponse {
  runs: RunResponse[];
}
```

### 3.2 UI Types (`types/index.ts`)

Limpos, camelCase, para uso nos componentes.

```typescript
// Brand
export interface Brand {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

// Project
export interface Project {
  id: string;
  brandId: string;
  name: string;
  objective?: string;
  channels?: string[];
  dueDate?: string;
  createdAt: string;
  updatedAt: string;
}

// Thread
export interface Thread {
  id: string;
  projectId: string;
  brandId: string;
  name: string;        // ← mapeado de 'title'
  status: string;
  modes?: string[];
  lastActivityAt?: string;
  createdAt: string;
  updatedAt: string;
}

// Run
export interface Stage {
  key: string;
  name: string;
  status: 'pending' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'skipped';
}

export interface Run {
  id: string;
  threadId: string;
  status: 'queued' | 'running' | 'waiting_approval' | 'completed' | 'failed';
  currentStage: string | null;
  stages: Stage[];
  createdAt: string;
  updatedAt: string;
}

// Artifact
export interface Artifact {
  path: string;
  name: string;
  type: 'markdown' | 'json' | 'yaml' | 'text';
  stageKey: string;
  runId: string;
}
```

---

## 4. Adapters

### 4.1 Brand Adapter

```typescript
// adapters/brand-adapter.ts
import type { BrandResponse } from '@/types/api';
import type { Brand } from '@/types';

export function mapBrand(response: BrandResponse): Brand {
  const now = new Date().toISOString();
  return {
    id: response.brand_id,
    name: response.name,
    createdAt: now,
    updatedAt: now,
  };
}

export function unmapBrand(brand: Partial<Brand>): { brand_id?: string; name?: string } {
  return {
    brand_id: brand.id,
    name: brand.name,
  };
}
```

### 4.2 Project Adapter

```typescript
// adapters/project-adapter.ts
import type { ProjectResponse } from '@/types/api';
import type { Project } from '@/types';

export function mapProject(response: ProjectResponse): Project {
  const now = new Date().toISOString();
  return {
    id: response.project_id,
    brandId: response.brand_id,
    name: response.name,
    objective: response.objective,
    channels: response.channels,
    dueDate: response.due_date,
    createdAt: now,
    updatedAt: now,
  };
}

export function unmapProject(project: Partial<Project>): {
  project_id?: string;
  brand_id?: string;
  name?: string;
  objective?: string;
  channels?: string[];
  due_date?: string;
} {
  return {
    project_id: project.id,
    brand_id: project.brandId,
    name: project.name,
    objective: project.objective,
    channels: project.channels,
    due_date: project.dueDate,
  };
}
```

### 4.3 Thread Adapter

```typescript
// adapters/thread-adapter.ts
import type { ThreadResponse } from '@/types/api';
import type { Thread } from '@/types';

export function mapThread(response: ThreadResponse): Thread {
  const now = new Date().toISOString();
  return {
    id: response.thread_id,
    projectId: response.project_id,
    brandId: response.brand_id,
    name: response.title,           // ← mapping: title → name
    status: response.status,
    modes: response.modes,
    lastActivityAt: response.last_activity_at,
    createdAt: now,
    updatedAt: now,
  };
}

export function unmapThread(thread: Partial<Thread>): {
  thread_id?: string;
  project_id?: string;
  brand_id?: string;
  title?: string;                  // ← mapping: name → title
} {
  return {
    thread_id: thread.id,
    project_id: thread.projectId,
    brand_id: thread.brandId,
    title: thread.name,
  };
}
```

### 4.4 Run Adapter

```typescript
// adapters/run-adapter.ts
import type { RunResponse, StageResponse } from '@/types/api';
import type { Run, Stage } from '@/types';

export function mapStage(response: StageResponse): Stage {
  return {
    key: response.key,
    name: response.name,
    status: response.status as Stage['status'],
  };
}

export function mapRun(response: RunResponse): Run {
  return {
    id: response.run_id,
    threadId: response.thread_id,
    status: response.status as Run['status'],
    currentStage: response.current_stage || null,
    stages: response.stages?.map(mapStage) || [],
    createdAt: response.created_at || new Date().toISOString(),
    updatedAt: response.updated_at || new Date().toISOString(),
  };
}
```

---

## 5. API Client

### 5.1 Base Client

```typescript
// lib/api.ts
const API_BASE = '/api/v2';

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail || `Request failed (${response.status})`;
    throw new APIError(detail, response.status, detail);
  }

  return response.json() as T;
}

export async function get<T>(path: string): Promise<T> {
  return fetchJson<T>(`${API_BASE}${path}`);
}

export async function post<T>(path: string, payload: unknown, idempotencyKey?: string): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }

  return fetchJson<T>(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
}

export async function patch<T>(path: string, payload: unknown, idempotencyKey?: string): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }

  return fetchJson<T>(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(payload),
  });
}

export async function del(path: string, idempotencyKey?: string): Promise<void> {
  const headers: Record<string, string> = {};
  
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers,
  });
  
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new APIError(payload.detail || `Delete failed (${response.status})`, response.status);
  }
}

export function buildIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
```

---

## 6. React Query Hooks

### 6.1 useBrands (Full CRUD)

```typescript
// hooks/api/use-brands.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { get, post, patch, del, buildIdempotencyKey } from '@/lib/api';
import type { BrandResponse, BrandsResponse } from '@/types/api';
import type { Brand } from '@/types';
import { mapBrand, unmapBrand } from '@/adapters/brand-adapter';
import { useToast } from '@/hooks/ui/use-toast';

const BRANDS_KEY = 'brands';

// GET /brands
export function useBrands() {
  return useQuery({
    queryKey: [BRANDS_KEY],
    queryFn: async () => {
      const response = await get<BrandsResponse>('/brands');
      return response.brands.map(mapBrand);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// POST /brands
export function useCreateBrand() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (name: string) => {
      const brandId = `brand-${Date.now().toString(36)}`;
      const payload = unmapBrand({ id: brandId, name });
      
      const response = await post<BrandResponse>(
        '/brands',
        payload,
        buildIdempotencyKey('brand-create')
      );
      
      return mapBrand(response);
    },
    onSuccess: (newBrand) => {
      queryClient.setQueryData([BRANDS_KEY], (old: Brand[] = []) => [...old, newBrand]);
      toast.success(`Brand "${newBrand.name}" created`);
    },
    onError: (error) => {
      toast.error('Failed to create brand', error.message);
    },
  });
}

// PATCH /brands/:id
export function useUpdateBrand() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Brand> }) => {
      const payload = unmapBrand(updates);
      const response = await patch<BrandResponse>(
        `/brands/${id}`,
        payload,
        buildIdempotencyKey(`brand-update-${id}`)
      );
      return mapBrand(response);
    },
    onMutate: async ({ id, updates }) => {
      await queryClient.cancelQueries([BRANDS_KEY]);
      const previous = queryClient.getQueryData<Brand[]>([BRANDS_KEY]);
      
      queryClient.setQueryData([BRANDS_KEY], (old: Brand[] = []) =>
        old.map(b => b.id === id ? { ...b, ...updates, updatedAt: new Date().toISOString() } : b)
      );
      
      return { previous };
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([BRANDS_KEY], context.previous);
      }
      toast.error('Failed to update brand');
    },
    onSettled: () => {
      queryClient.invalidateQueries([BRANDS_KEY]);
    },
  });
}

// DELETE /brands/:id
export function useDeleteBrand() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (brandId: string) => {
      await del(`/brands/${brandId}`, buildIdempotencyKey(`brand-delete-${brandId}`));
      return brandId;
    },
    onMutate: async (brandId) => {
      await queryClient.cancelQueries([BRANDS_KEY]);
      const previous = queryClient.getQueryData<Brand[]>([BRANDS_KEY]);
      
      // Optimistic: remove imediatamente
      queryClient.setQueryData([BRANDS_KEY], (old: Brand[] = []) =>
        old.filter(b => b.id !== brandId)
      );
      
      return { previous };
    },
    onError: (err, brandId, context) => {
      if (context?.previous) {
        queryClient.setQueryData([BRANDS_KEY], context.previous);
      }
      toast.error('Failed to delete brand');
    },
    onSettled: () => {
      queryClient.invalidateQueries([BRANDS_KEY]);
    },
    onSuccess: () => {
      toast.success('Brand deleted');
    },
  });
}
```

### 6.2 useProjects (Full CRUD)

```typescript
// hooks/api/use-projects.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { get, post, patch, del, buildIdempotencyKey } from '@/lib/api';
import type { ProjectResponse, ProjectsResponse } from '@/types/api';
import type { Project } from '@/types';
import { mapProject, unmapProject } from '@/adapters/project-adapter';
import { useToast } from '@/hooks/ui/use-toast';

const PROJECTS_KEY = 'projects';

export function useProjects(brandId: string | null) {
  return useQuery({
    queryKey: [PROJECTS_KEY, brandId],
    queryFn: async () => {
      if (!brandId) return [];
      const response = await get<ProjectsResponse>(`/projects?brand_id=${encodeURIComponent(brandId)}`);
      return response.projects.map(mapProject);
    },
    enabled: !!brandId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ brandId, name }: { brandId: string; name: string }) => {
      const projectId = `proj-${Date.now().toString(36)}`;
      const payload = unmapProject({
        id: projectId,
        brandId,
        name,
        objective: '',
        channels: [],
      });
      
      const response = await post<ProjectResponse>(
        '/projects',
        payload,
        buildIdempotencyKey('project-create')
      );
      
      return mapProject(response);
    },
    onSuccess: (newProject) => {
      queryClient.setQueryData([PROJECTS_KEY, newProject.brandId], (old: Project[] = []) => [...old, newProject]);
      toast.success(`Project "${newProject.name}" created`);
    },
    onError: (error) => {
      toast.error('Failed to create project', error.message);
    },
  });
}

export function useUpdateProject() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Project> }) => {
      const payload = unmapProject(updates);
      const response = await patch<ProjectResponse>(
        `/projects/${id}`,
        payload,
        buildIdempotencyKey(`project-update-${id}`)
      );
      return mapProject(response);
    },
    onMutate: async ({ id, updates }) => {
      const brandId = updates.brandId;
      await queryClient.cancelQueries([PROJECTS_KEY, brandId]);
      const previous = queryClient.getQueryData<Project[]>([PROJECTS_KEY, brandId]);
      
      queryClient.setQueryData([PROJECTS_KEY, brandId], (old: Project[] = []) =>
        old.map(p => p.id === id ? { ...p, ...updates, updatedAt: new Date().toISOString() } : p)
      );
      
      return { previous };
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([PROJECTS_KEY, vars.updates.brandId], context.previous);
      }
      toast.error('Failed to update project');
    },
    onSettled: (data) => {
      queryClient.invalidateQueries([PROJECTS_KEY, data?.brandId]);
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ id, brandId }: { id: string; brandId: string }) => {
      await del(`/projects/${id}`, buildIdempotencyKey(`project-delete-${id}`));
      return { id, brandId };
    },
    onMutate: async ({ id, brandId }) => {
      await queryClient.cancelQueries([PROJECTS_KEY, brandId]);
      const previous = queryClient.getQueryData<Project[]>([PROJECTS_KEY, brandId]);
      
      queryClient.setQueryData([PROJECTS_KEY, brandId], (old: Project[] = []) =>
        old.filter(p => p.id !== id)
      );
      
      return { previous };
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([PROJECTS_KEY, vars.brandId], context.previous);
      }
      toast.error('Failed to delete project');
    },
    onSettled: (data) => {
      queryClient.invalidateQueries([PROJECTS_KEY, data?.brandId]);
    },
    onSuccess: () => {
      toast.success('Project deleted');
    },
  });
}
```

### 6.3 useThreads (Full CRUD)

```typescript
// hooks/api/use-threads.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { get, post, patch, del, buildIdempotencyKey } from '@/lib/api';
import type { ThreadResponse, ThreadsResponse } from '@/types/api';
import type { Thread } from '@/types';
import { mapThread, unmapThread } from '@/adapters/thread-adapter';
import { useToast } from '@/hooks/ui/use-toast';

const THREADS_KEY = 'threads';

export function useThreads(projectId: string | null) {
  return useQuery({
    queryKey: [THREADS_KEY, projectId],
    queryFn: async () => {
      if (!projectId) return [];
      const response = await get<ThreadsResponse>(`/threads?project_id=${encodeURIComponent(projectId)}`);
      return response.threads.map(mapThread);
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateThread() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ brandId, projectId, title }: { brandId: string; projectId: string; title: string }) => {
      const threadId = `thread-${Date.now().toString(36)}`;
      const payload = unmapThread({
        id: threadId,
        projectId,
        brandId,
        name: title,
      });
      
      const response = await post<ThreadResponse>(
        '/threads',
        payload,
        buildIdempotencyKey('thread-create')
      );
      
      return mapThread(response);
    },
    onSuccess: (newThread) => {
      queryClient.setQueryData([THREADS_KEY, newThread.projectId], (old: Thread[] = []) => [...old, newThread]);
      toast.success(`Thread "${newThread.name}" created`);
    },
    onError: (error) => {
      toast.error('Failed to create thread', error.message);
    },
  });
}

export function useUpdateThread() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Thread> }) => {
      const payload = unmapThread(updates);
      const response = await patch<ThreadResponse>(
        `/threads/${id}`,
        payload,
        buildIdempotencyKey(`thread-update-${id}`)
      );
      return mapThread(response);
    },
    onMutate: async ({ id, updates }) => {
      const projectId = updates.projectId;
      await queryClient.cancelQueries([THREADS_KEY, projectId]);
      const previous = queryClient.getQueryData<Thread[]>([THREADS_KEY, projectId]);
      
      queryClient.setQueryData([THREADS_KEY, projectId], (old: Thread[] = []) =>
        old.map(t => t.id === id ? { ...t, ...updates, updatedAt: new Date().toISOString() } : t)
      );
      
      return { previous };
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([THREADS_KEY, vars.updates.projectId], context.previous);
      }
      toast.error('Failed to update thread');
    },
    onSettled: (data) => {
      queryClient.invalidateQueries([THREADS_KEY, data?.projectId]);
    },
  });
}

export function useDeleteThread() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ id, projectId }: { id: string; projectId: string }) => {
      await del(`/threads/${id}`, buildIdempotencyKey(`thread-delete-${id}`));
      return { id, projectId };
    },
    onMutate: async ({ id, projectId }) => {
      await queryClient.cancelQueries([THREADS_KEY, projectId]);
      const previous = queryClient.getQueryData<Thread[]>([THREADS_KEY, projectId]);
      
      queryClient.setQueryData([THREADS_KEY, projectId], (old: Thread[] = []) =>
        old.filter(t => t.id !== id)
      );
      
      return { previous };
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([THREADS_KEY, vars.projectId], context.previous);
      }
      toast.error('Failed to delete thread');
    },
    onSettled: (data) => {
      queryClient.invalidateQueries([THREADS_KEY, data?.projectId]);
    },
    onSuccess: () => {
      toast.success('Thread deleted');
    },
  });
}
```

### 6.4 useRuns (com Polling)

```typescript
// hooks/api/use-runs.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { get, post, buildIdempotencyKey } from '@/lib/api';
import type { RunResponse, RunsResponse } from '@/types/api';
import type { Run } from '@/types';
import { mapRun } from '@/adapters/run-adapter';
import { useToast } from '@/hooks/ui/use-toast';

const RUNS_KEY = 'runs';

export function useRuns(threadId: string | null) {
  return useQuery({
    queryKey: [RUNS_KEY, threadId],
    queryFn: async () => {
      if (!threadId) return [];
      const response = await get<RunsResponse>(`/threads/${encodeURIComponent(threadId)}/workflow-runs`);
      return response.runs.map(mapRun);
    },
    enabled: !!threadId,
    staleTime: 10 * 1000, // 10 seconds
    
    // Polling dinâmico
    refetchInterval: (data) => {
      const hasRunning = data?.some(run => 
        run.status === 'running' || run.status === 'queued'
      );
      return hasRunning ? 2000 : false; // 2s se running, senão para
    },
    
    // Retry exponencial
    retry: (failureCount, error: APIError) => {
      if (error.status >= 500) return failureCount < 3;
      return false;
    },
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({
      threadId,
      mode,
      requestText,
    }: {
      threadId: string;
      mode: string;
      requestText: string;
    }) => {
      const response = await post<{ run_id: string; status: string }>(
        `/threads/${encodeURIComponent(threadId)}/workflow-runs`,
        {
          mode,
          request_text: requestText,
          skill_overrides: {},
        },
        buildIdempotencyKey('workflow-run')
      );
      return response.run_id;
    },
    onSuccess: (_, variables) => {
      toast.success('Workflow started');
      queryClient.invalidateQueries([RUNS_KEY, variables.threadId]);
    },
    onError: (error) => {
      toast.error('Failed to start workflow', error.message);
    },
  });
}

export function useResumeRun() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ runId, threadId }: { runId: string; threadId: string }) => {
      const response = await post<{ run_id: string; status: string }>(
        `/workflow-runs/${encodeURIComponent(runId)}/resume`,
        {},
        buildIdempotencyKey(`run-resume-${runId}`)
      );
      return response;
    },
    onSuccess: (_, variables) => {
      toast.success('Workflow resumed');
      queryClient.invalidateQueries([RUNS_KEY, variables.threadId]);
    },
    onError: (error) => {
      toast.error('Failed to resume workflow', error.message);
    },
  });
}

export function useGrantApproval() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ approvalId, threadId }: { approvalId: string; threadId: string }) => {
      await post(
        `/approvals/${encodeURIComponent(approvalId)}/grant`,
        {},
        buildIdempotencyKey(`approval-grant-${approvalId}`)
      );
    },
    onSuccess: (_, variables) => {
      toast.success('Stage approved');
      queryClient.invalidateQueries([RUNS_KEY, variables.threadId]);
    },
    onError: (error) => {
      toast.error('Failed to approve', error.message);
    },
  });
}
```

---

## 7. Toast System

### 7.1 Types

```typescript
// hooks/ui/use-toast.ts
export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}
```

### 7.2 Store

```typescript
// hooks/ui/use-toast.ts
import { useState, useCallback } from 'react';

const DEFAULT_DURATION = 5000;

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).slice(2);
    const newToast = { ...toast, id, duration: toast.duration || DEFAULT_DURATION };
    
    setToasts((prev) => [...prev, newToast]);
    
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, newToast.duration);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const success = useCallback((title: string, message?: string) => {
    addToast({ type: 'success', title, message });
  }, [addToast]);

  const error = useCallback((title: string, message?: string) => {
    addToast({ type: 'error', title, message });
  }, [addToast]);

  const warning = useCallback((title: string, message?: string) => {
    addToast({ type: 'warning', title, message });
  }, [addToast]);

  const info = useCallback((title: string, message?: string) => {
    addToast({ type: 'info', title, message });
  }, [addToast]);

  return { toasts, addToast, removeToast, success, error, warning, info };
}
```

### 7.3 Component

```tsx
// components/ui/toast-container.tsx
import { useToast } from '@/hooks/ui/use-toast';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const colors = {
  success: 'bg-vm-success/10 border-vm-success text-vm-success',
  error: 'bg-vm-error/10 border-vm-error text-vm-error',
  warning: 'bg-vm-warning/10 border-vm-warning text-vm-warning',
  info: 'bg-vm-primary/10 border-vm-primary text-vm-primary',
};

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => {
        const Icon = icons[toast.type];
        return (
          <div
            key={toast.id}
            className={cn(
              'flex items-start gap-3 p-4 rounded-vm-lg border shadow-vm-lg animate-in slide-in-from-right',
              colors[toast.type]
            )}
          >
            <Icon className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm">{toast.title}</p>
              {toast.message && (
                <p className="text-xs mt-1 opacity-80">{toast.message}</p>
              )}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="opacity-60 hover:opacity-100 transition-opacity"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
```

---

## 8. Integração nos Componentes

### 8.1 NavigationPanel

```tsx
// Modificações necessárias em navigation-panel.tsx

import { useBrands, useCreateBrand } from '@/hooks/api/use-brands';
import { useProjects, useCreateProject } from '@/hooks/api/use-projects';
import { useThreads, useCreateThread } from '@/hooks/api/use-threads';
import { Loader2 } from 'lucide-react';

export function NavigationPanel() {
  const { activeBrandId, activeProjectId, selectBrand, selectProject, selectThread } = useStore();
  
  // Substitui mock data por hooks reais
  const { data: brands = [], isLoading: isLoadingBrands } = useBrands();
  const { data: projects = [], isLoading: isLoadingProjects } = useProjects(activeBrandId);
  const { data: threads = [], isLoading: isLoadingThreads } = useThreads(activeProjectId);

  // Loading states
  if (isLoadingBrands) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-5 h-5 animate-spin text-vm-ink-muted" />
      </div>
    );
  }

  // Resto do componente permanece igual
  // pois `brands`, `projects`, `threads` têm a mesma interface (Brand[], etc.)
}
```

### 8.2 CommandRail

```tsx
// Modificações em command-rail.tsx

import { useRuns, useResumeRun } from '@/hooks/api/use-runs';
import { Loader2 } from 'lucide-react';

export function CommandRail() {
  const { activeThreadId, activeRunId } = useStore();
  const { data: runs = [], isLoading } = useRuns(activeThreadId);
  const activeRun = runs.find(r => r.id === activeRunId);
  const resumeRun = useResumeRun();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-vm-ink-muted" />
      </div>
    );
  }

  // Actions
  <CommandItem 
    icon={Play} 
    label="Resume Workflow"
    onClick={() => activeRun && resumeRun.mutate({ runId: activeRun.id, threadId: activeThreadId! })}
    isLoading={resumeRun.isPending}
  />
}
```

---

## 9. Decisiones e Restrições

### 9.1 Decidido
- **Adapter Pattern Híbrido:** Types exatas do backend + types limpas para UI
- **React Query:** Caching, polling, retries automáticos
- **Optimistic Updates Híbridos:** Create pessimistic, Update/Delete optimistic
- **Toast Global:** Notificações em top-right, auto-dismiss
- **Zero mudanças no backend:** Toda adaptação no frontend

### 9.2 Endpoints Utilizados

| Recurso | GET | POST | PATCH | DELETE |
|---------|-----|------|-------|--------|
| Brands | `/brands` | `/brands` | `/brands/:id` | `/brands/:id` |
| Projects | `/projects?brand_id=` | `/projects` | `/projects/:id` | `/projects/:id` |
| Threads | `/threads?project_id=` | `/threads` | `/threads/:id` | `/threads/:id` |
| Runs | `/threads/:id/workflow-runs` | `/threads/:id/workflow-runs` | — | — |
| Actions | — | `/workflow-runs/:id/resume` | — | — |
| Approvals | — | `/approvals/:id/grant` | — | — |

### 9.3 Cache Invalidation

| Mutação | Queries Invalidadas |
|---------|---------------------|
| Create Brand | `['brands']` |
| Update Brand | `['brands']` |
| Delete Brand | `['brands']` |
| Create Project | `['projects', brandId]` |
| Update Project | `['projects', brandId]` |
| Delete Project | `['projects', brandId]` |
| Create Thread | `['threads', projectId]` |
| Update Thread | `['threads', projectId]` |
| Delete Thread | `['threads', projectId]` |
| Start Run | `['runs', threadId]` |
| Resume Run | `['runs', threadId]` |
| Grant Approval | `['runs', threadId]` |

---

## 10. Notas de Implementação

1. **Idempotency:** Todos os POST/PATCH/DELETE incluem `Idempotency-Key` header
2. **Error Handling:** APIError captura status e detail; toast mostra mensagem amigável
3. **Polling:** Runs fazem poll a cada 2s quando status === 'running' ou 'queued'
4. **Retry:** Erros 5xx fazem retry exponencial (1s, 2s, 4s, max 10s)
5. **Loading States:** Cada hook expõe `isLoading` para UI de skeleton/spinner
6. **Type Safety:** Adapters garantem que backend pode mudar sem quebrar UI

---

*Design aprovado em: 2026-03-02*
*Próximo passo: Plano de implementação via writing-plans skill*
