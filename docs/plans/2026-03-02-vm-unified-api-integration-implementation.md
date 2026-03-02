# VM Unified API Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrar vm-unified frontend com vm_webapp backend API usando Adapter Pattern e React Query, sem modificar o backend.

**Architecture:** Tipos exatas do backend em `types/api.ts`, tipos limpos em `types/index.ts`, adapters fazem conversão. React Query para server state, Zustand para UI state. Toast global para feedback.

**Tech Stack:** React 18, TypeScript, React Query (@tanstack/react-query), Zustand, Tailwind CSS

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

Expected: `added XX packages in Xs`

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
git commit -m "feat(vm-unified): add React Query with devtools"
```

---

## Task 2: API Client Base

**Files:**
- Create: `vm-unified/src/lib/api.ts`

**Step 1: Criar API client com suporte a Idempotency-Key**

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

export async function patch<T>(path: string, payload: unknown, idempotencyKey?: string): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey
  }

  return fetchJson<T>(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(payload),
  })
}

export async function del(path: string, idempotencyKey?: string): Promise<void> {
  const headers: Record<string, string> = {}
  
  if (idempotencyKey) {
    headers['Idempotency-Key'] = idempotencyKey
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers,
  })
  
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new APIError(payload.detail || `Delete failed (${response.status})`, response.status)
  }
}

export function buildIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/lib/api.ts
git commit -m "feat(vm-unified): add API client with error handling and idempotency"
```

---

## Task 3: Backend Types (types/api.ts)

**Files:**
- Create: `vm-unified/src/types/api.ts`

**Step 1: Criar tipos exatas do backend (snake_case)**

Create: `vm-unified/src/types/api.ts`

```typescript
// Brand
export interface BrandResponse {
  brand_id: string
  name: string
}

export interface BrandsResponse {
  brands: BrandResponse[]
}

// Project
export interface ProjectResponse {
  project_id: string
  brand_id: string
  name: string
  objective?: string
  channels?: string[]
  due_date?: string
}

export interface ProjectsResponse {
  projects: ProjectResponse[]
}

// Thread
export interface ThreadResponse {
  thread_id: string
  project_id: string
  brand_id: string
  title: string
  status: string
  modes?: string[]
  last_activity_at?: string
}

export interface ThreadsResponse {
  threads: ThreadResponse[]
}

// Run
export interface StageResponse {
  key: string
  name: string
  status: string
}

export interface RunResponse {
  run_id: string
  thread_id: string
  status: string
  current_stage?: string
  stages?: StageResponse[]
  created_at?: string
  updated_at?: string
}

export interface RunsResponse {
  runs: RunResponse[]
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/types/api.ts
git commit -m "feat(vm-unified): add backend API types (snake_case)"
```

---

## Task 4: Adapters

**Files:**
- Create: `vm-unified/src/adapters/brand-adapter.ts`
- Create: `vm-unified/src/adapters/project-adapter.ts`
- Create: `vm-unified/src/adapters/thread-adapter.ts`
- Create: `vm-unified/src/adapters/run-adapter.ts`

**Step 1: Brand Adapter**

Create: `vm-unified/src/adapters/brand-adapter.ts`

```typescript
import type { BrandResponse } from '@/types/api'
import type { Brand } from '@/types'

export function mapBrand(response: BrandResponse): Brand {
  const now = new Date().toISOString()
  return {
    id: response.brand_id,
    name: response.name,
    createdAt: now,
    updatedAt: now,
  }
}

export function unmapBrand(brand: Partial<Brand>): { brand_id?: string; name?: string } {
  return {
    brand_id: brand.id,
    name: brand.name,
  }
}
```

**Step 2: Project Adapter**

Create: `vm-unified/src/adapters/project-adapter.ts`

```typescript
import type { ProjectResponse } from '@/types/api'
import type { Project } from '@/types'

export function mapProject(response: ProjectResponse): Project {
  const now = new Date().toISOString()
  return {
    id: response.project_id,
    brandId: response.brand_id,
    name: response.name,
    objective: response.objective,
    channels: response.channels,
    dueDate: response.due_date,
    createdAt: now,
    updatedAt: now,
  }
}

export function unmapProject(project: Partial<Project>): {
  project_id?: string
  brand_id?: string
  name?: string
  objective?: string
  channels?: string[]
  due_date?: string
} {
  return {
    project_id: project.id,
    brand_id: project.brandId,
    name: project.name,
    objective: project.objective,
    channels: project.channels,
    due_date: project.dueDate,
  }
}
```

**Step 3: Thread Adapter**

Create: `vm-unified/src/adapters/thread-adapter.ts`

```typescript
import type { ThreadResponse } from '@/types/api'
import type { Thread } from '@/types'

export function mapThread(response: ThreadResponse): Thread {
  const now = new Date().toISOString()
  return {
    id: response.thread_id,
    projectId: response.project_id,
    brandId: response.brand_id,
    name: response.title,
    status: response.status,
    modes: response.modes,
    lastActivityAt: response.last_activity_at,
    createdAt: now,
    updatedAt: now,
  }
}

export function unmapThread(thread: Partial<Thread>): {
  thread_id?: string
  project_id?: string
  brand_id?: string
  title?: string
} {
  return {
    thread_id: thread.id,
    project_id: thread.projectId,
    brand_id: thread.brandId,
    title: thread.name,
  }
}
```

**Step 4: Run Adapter**

Create: `vm-unified/src/adapters/run-adapter.ts`

```typescript
import type { RunResponse, StageResponse } from '@/types/api'
import type { Run, Stage } from '@/types'

export function mapStage(response: StageResponse): Stage {
  return {
    key: response.key,
    name: response.name,
    status: response.status as Stage['status'],
  }
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
  }
}
```

**Step 5: Commit**

```bash
git add 09-tools/web/vm-unified/src/adapters/
git commit -m "feat(vm-unified): add adapters for Brand, Project, Thread, Run"
```

---

## Task 5: Toast System

**Files:**
- Create: `vm-unified/src/hooks/ui/use-toast.ts`
- Create: `vm-unified/src/components/ui/toast-container.tsx`

**Step 1: Toast Hook**

Create: `vm-unified/src/hooks/ui/use-toast.ts`

```typescript
import { useState, useCallback } from 'react'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number
}

const DEFAULT_DURATION = 5000

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).slice(2)
    const newToast = { ...toast, id, duration: toast.duration || DEFAULT_DURATION }
    
    setToasts((prev) => [...prev, newToast])
    
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, newToast.duration)
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const success = useCallback((title: string, message?: string) => {
    addToast({ type: 'success', title, message })
  }, [addToast])

  const error = useCallback((title: string, message?: string) => {
    addToast({ type: 'error', title, message })
  }, [addToast])

  const warning = useCallback((title: string, message?: string) => {
    addToast({ type: 'warning', title, message })
  }, [addToast])

  const info = useCallback((title: string, message?: string) => {
    addToast({ type: 'info', title, message })
  }, [addToast])

  return { toasts, addToast, removeToast, success, error, warning, info }
}
```

**Step 2: Toast Container Component**

Create: `vm-unified/src/components/ui/toast-container.tsx`

```typescript
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Toast } from '@/hooks/ui/use-toast'

const icons = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const colors = {
  success: 'bg-vm-success/10 border-vm-success text-vm-success',
  error: 'bg-vm-error/10 border-vm-error text-vm-error',
  warning: 'bg-vm-warning/10 border-vm-warning text-vm-warning',
  info: 'bg-vm-primary/10 border-vm-primary text-vm-primary',
}

interface ToastContainerProps {
  toasts: Toast[]
  onRemove: (id: string) => void
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((toast) => {
        const Icon = icons[toast.type]
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
              onClick={() => onRemove(toast.id)}
              className="opacity-60 hover:opacity-100 transition-opacity"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
```

**Step 3: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/ui/use-toast.ts
git add 09-tools/web/vm-unified/src/components/ui/toast-container.tsx
git commit -m "feat(vm-unified): add toast notification system"
```

---

## Task 6: useBrands Hook (Full CRUD)

**Files:**
- Create: `vm-unified/src/hooks/api/use-brands.ts`

**Step 1: Criar hook com todas as operações**

Create: `vm-unified/src/hooks/api/use-brands.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, patch, del, buildIdempotencyKey } from '@/lib/api'
import type { BrandResponse, BrandsResponse } from '@/types/api'
import type { Brand } from '@/types'
import { mapBrand, unmapBrand } from '@/adapters/brand-adapter'
import { useToast } from '@/hooks/ui/use-toast'

const BRANDS_KEY = 'brands'

// GET /brands
export function useBrands() {
  return useQuery({
    queryKey: [BRANDS_KEY],
    queryFn: async () => {
      const response = await get<BrandsResponse>('/brands')
      return response.brands.map(mapBrand)
    },
    staleTime: 5 * 60 * 1000,
  })
}

// POST /brands
export function useCreateBrand() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (name: string) => {
      const brandId = `brand-${Date.now().toString(36)}`
      const payload = unmapBrand({ id: brandId, name })
      
      const response = await post<BrandResponse>(
        '/brands',
        payload,
        buildIdempotencyKey('brand-create')
      )
      
      return mapBrand(response)
    },
    onSuccess: (newBrand) => {
      queryClient.setQueryData([BRANDS_KEY], (old: Brand[] = []) => [...old, newBrand])
      toast.success(`Brand "${newBrand.name}" created`)
    },
    onError: (error) => {
      toast.error('Failed to create brand', error.message)
    },
  })
}

// PATCH /brands/:id
export function useUpdateBrand() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Brand> }) => {
      const payload = unmapBrand(updates)
      const response = await patch<BrandResponse>(
        `/brands/${id}`,
        payload,
        buildIdempotencyKey(`brand-update-${id}`)
      )
      return mapBrand(response)
    },
    onMutate: async ({ id, updates }) => {
      await queryClient.cancelQueries([BRANDS_KEY])
      const previous = queryClient.getQueryData<Brand[]>([BRANDS_KEY])
      
      queryClient.setQueryData([BRANDS_KEY], (old: Brand[] = []) =>
        old.map(b => b.id === id ? { ...b, ...updates, updatedAt: new Date().toISOString() } : b)
      )
      
      return { previous }
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([BRANDS_KEY], context.previous)
      }
      toast.error('Failed to update brand')
    },
    onSettled: () => {
      queryClient.invalidateQueries([BRANDS_KEY])
    },
  })
}

// DELETE /brands/:id
export function useDeleteBrand() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (brandId: string) => {
      await del(`/brands/${brandId}`, buildIdempotencyKey(`brand-delete-${brandId}`))
      return brandId
    },
    onMutate: async (brandId) => {
      await queryClient.cancelQueries([BRANDS_KEY])
      const previous = queryClient.getQueryData<Brand[]>([BRANDS_KEY])
      
      queryClient.setQueryData([BRANDS_KEY], (old: Brand[] = []) =>
        old.filter(b => b.id !== brandId)
      )
      
      return { previous }
    },
    onError: (err, brandId, context) => {
      if (context?.previous) {
        queryClient.setQueryData([BRANDS_KEY], context.previous)
      }
      toast.error('Failed to delete brand')
    },
    onSettled: () => {
      queryClient.invalidateQueries([BRANDS_KEY])
    },
    onSuccess: () => {
      toast.success('Brand deleted')
    },
  })
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/api/use-brands.ts
git commit -m "feat(vm-unified): add useBrands hook with full CRUD"
```

---

## Task 7: useProjects Hook (Full CRUD)

**Files:**
- Create: `vm-unified/src/hooks/api/use-projects.ts`

**Step 1: Criar hook**

Create: `vm-unified/src/hooks/api/use-projects.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, patch, del, buildIdempotencyKey } from '@/lib/api'
import type { ProjectResponse, ProjectsResponse } from '@/types/api'
import type { Project } from '@/types'
import { mapProject, unmapProject } from '@/adapters/project-adapter'
import { useToast } from '@/hooks/ui/use-toast'

const PROJECTS_KEY = 'projects'

export function useProjects(brandId: string | null) {
  return useQuery({
    queryKey: [PROJECTS_KEY, brandId],
    queryFn: async () => {
      if (!brandId) return []
      const response = await get<ProjectsResponse>(`/projects?brand_id=${encodeURIComponent(brandId)}`)
      return response.projects.map(mapProject)
    },
    enabled: !!brandId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ brandId, name }: { brandId: string; name: string }) => {
      const projectId = `proj-${Date.now().toString(36)}`
      const payload = unmapProject({
        id: projectId,
        brandId,
        name,
        objective: '',
        channels: [],
      })
      
      const response = await post<ProjectResponse>(
        '/projects',
        payload,
        buildIdempotencyKey('project-create')
      )
      
      return mapProject(response)
    },
    onSuccess: (newProject) => {
      queryClient.setQueryData([PROJECTS_KEY, newProject.brandId], (old: Project[] = []) => [...old, newProject])
      toast.success(`Project "${newProject.name}" created`)
    },
    onError: (error) => {
      toast.error('Failed to create project', error.message)
    },
  })
}

export function useUpdateProject() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Project> }) => {
      const payload = unmapProject(updates)
      const response = await patch<ProjectResponse>(
        `/projects/${id}`,
        payload,
        buildIdempotencyKey(`project-update-${id}`)
      )
      return mapProject(response)
    },
    onMutate: async ({ id, updates }) => {
      const brandId = updates.brandId
      await queryClient.cancelQueries([PROJECTS_KEY, brandId])
      const previous = queryClient.getQueryData<Project[]>([PROJECTS_KEY, brandId])
      
      queryClient.setQueryData([PROJECTS_KEY, brandId], (old: Project[] = []) =>
        old.map(p => p.id === id ? { ...p, ...updates, updatedAt: new Date().toISOString() } : p)
      )
      
      return { previous }
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([PROJECTS_KEY, vars.updates.brandId], context.previous)
      }
      toast.error('Failed to update project')
    },
    onSettled: (data) => {
      queryClient.invalidateQueries([PROJECTS_KEY, data?.brandId])
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ id, brandId }: { id: string; brandId: string }) => {
      await del(`/projects/${id}`, buildIdempotencyKey(`project-delete-${id}`))
      return { id, brandId }
    },
    onMutate: async ({ id, brandId }) => {
      await queryClient.cancelQueries([PROJECTS_KEY, brandId])
      const previous = queryClient.getQueryData<Project[]>([PROJECTS_KEY, brandId])
      
      queryClient.setQueryData([PROJECTS_KEY, brandId], (old: Project[] = []) =>
        old.filter(p => p.id !== id)
      )
      
      return { previous }
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([PROJECTS_KEY, vars.brandId], context.previous)
      }
      toast.error('Failed to delete project')
    },
    onSettled: (data) => {
      queryClient.invalidateQueries([PROJECTS_KEY, data?.brandId])
    },
    onSuccess: () => {
      toast.success('Project deleted')
    },
  })
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/api/use-projects.ts
git commit -m "feat(vm-unified): add useProjects hook with full CRUD"
```

---

## Task 8: useThreads Hook (Full CRUD)

**Files:**
- Create: `vm-unified/src/hooks/api/use-threads.ts`

**Step 1: Criar hook**

Create: `vm-unified/src/hooks/api/use-threads.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, patch, del, buildIdempotencyKey } from '@/lib/api'
import type { ThreadResponse, ThreadsResponse } from '@/types/api'
import type { Thread } from '@/types'
import { mapThread, unmapThread } from '@/adapters/thread-adapter'
import { useToast } from '@/hooks/ui/use-toast'

const THREADS_KEY = 'threads'

export function useThreads(projectId: string | null) {
  return useQuery({
    queryKey: [THREADS_KEY, projectId],
    queryFn: async () => {
      if (!projectId) return []
      const response = await get<ThreadsResponse>(`/threads?project_id=${encodeURIComponent(projectId)}`)
      return response.threads.map(mapThread)
    },
    enabled: !!projectId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCreateThread() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ brandId, projectId, title }: { brandId: string; projectId: string; title: string }) => {
      const threadId = `thread-${Date.now().toString(36)}`
      const payload = unmapThread({
        id: threadId,
        projectId,
        brandId,
        name: title,
      })
      
      const response = await post<ThreadResponse>(
        '/threads',
        payload,
        buildIdempotencyKey('thread-create')
      )
      
      return mapThread(response)
    },
    onSuccess: (newThread) => {
      queryClient.setQueryData([THREADS_KEY, newThread.projectId], (old: Thread[] = []) => [...old, newThread])
      toast.success(`Thread "${newThread.name}" created`)
    },
    onError: (error) => {
      toast.error('Failed to create thread', error.message)
    },
  })
}

export function useUpdateThread() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Thread> }) => {
      const payload = unmapThread(updates)
      const response = await patch<ThreadResponse>(
        `/threads/${id}`,
        payload,
        buildIdempotencyKey(`thread-update-${id}`)
      )
      return mapThread(response)
    },
    onMutate: async ({ id, updates }) => {
      const projectId = updates.projectId
      await queryClient.cancelQueries([THREADS_KEY, projectId])
      const previous = queryClient.getQueryData<Thread[]>([THREADS_KEY, projectId])
      
      queryClient.setQueryData([THREADS_KEY, projectId], (old: Thread[] = []) =>
        old.map(t => t.id === id ? { ...t, ...updates, updatedAt: new Date().toISOString() } : t)
      )
      
      return { previous }
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([THREADS_KEY, vars.updates.projectId], context.previous)
      }
      toast.error('Failed to update thread')
    },
    onSettled: (data) => {
      queryClient.invalidateQueries([THREADS_KEY, data?.projectId])
    },
  })
}

export function useDeleteThread() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ id, projectId }: { id: string; projectId: string }) => {
      await del(`/threads/${id}`, buildIdempotencyKey(`thread-delete-${id}`))
      return { id, projectId }
    },
    onMutate: async ({ id, projectId }) => {
      await queryClient.cancelQueries([THREADS_KEY, projectId])
      const previous = queryClient.getQueryData<Thread[]>([THREADS_KEY, projectId])
      
      queryClient.setQueryData([THREADS_KEY, projectId], (old: Thread[] = []) =>
        old.filter(t => t.id !== id)
      )
      
      return { previous }
    },
    onError: (err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([THREADS_KEY, vars.projectId], context.previous)
      }
      toast.error('Failed to delete thread')
    },
    onSettled: (data) => {
      queryClient.invalidateQueries([THREADS_KEY, data?.projectId])
    },
    onSuccess: () => {
      toast.success('Thread deleted')
    },
  })
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/api/use-threads.ts
git commit -m "feat(vm-unified): add useThreads hook with full CRUD"
```

---

## Task 9: useRuns Hook (com Polling)

**Files:**
- Create: `vm-unified/src/hooks/api/use-runs.ts`

**Step 1: Criar hook com polling dinâmico**

Create: `vm-unified/src/hooks/api/use-runs.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, buildIdempotencyKey } from '@/lib/api'
import type { RunResponse, RunsResponse } from '@/types/api'
import type { Run } from '@/types'
import { mapRun } from '@/adapters/run-adapter'
import { useToast } from '@/hooks/ui/use-toast'

const RUNS_KEY = 'runs'

export function useRuns(threadId: string | null) {
  return useQuery({
    queryKey: [RUNS_KEY, threadId],
    queryFn: async () => {
      if (!threadId) return []
      const response = await get<RunsResponse>(`/threads/${encodeURIComponent(threadId)}/workflow-runs`)
      return response.runs.map(mapRun)
    },
    enabled: !!threadId,
    staleTime: 10 * 1000,
    
    refetchInterval: (data) => {
      const hasRunning = data?.some(run => 
        run.status === 'running' || run.status === 'queued'
      )
      return hasRunning ? 2000 : false
    },
    
    retry: (failureCount, error: APIError) => {
      if (error.status >= 500) return failureCount < 3
      return false
    },
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
  })
}

export function useCreateRun() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

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
      toast.success('Workflow started')
      queryClient.invalidateQueries([RUNS_KEY, variables.threadId])
    },
    onError: (error) => {
      toast.error('Failed to start workflow', error.message)
    },
  })
}

export function useResumeRun() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ runId, threadId }: { runId: string; threadId: string }) => {
      const response = await post<{ run_id: string; status: string }>(
        `/workflow-runs/${encodeURIComponent(runId)}/resume`,
        {},
        buildIdempotencyKey(`run-resume-${runId}`)
      )
      return response
    },
    onSuccess: (_, variables) => {
      toast.success('Workflow resumed')
      queryClient.invalidateQueries([RUNS_KEY, variables.threadId])
    },
    onError: (error) => {
      toast.error('Failed to resume workflow', error.message)
    },
  })
}

export function useGrantApproval() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ approvalId, threadId }: { approvalId: string; threadId: string }) => {
      await post(
        `/approvals/${encodeURIComponent(approvalId)}/grant`,
        {},
        buildIdempotencyKey(`approval-grant-${approvalId}`)
      )
    },
    onSuccess: (_, variables) => {
      toast.success('Stage approved')
      queryClient.invalidateQueries([RUNS_KEY, variables.threadId])
    },
    onError: (error) => {
      toast.error('Failed to approve', error.message)
    },
  })
}
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/api/use-runs.ts
git commit -m "feat(vm-unified): add useRuns hook with polling"
```

---

## Task 10: Integrar na NavigationPanel

**Files:**
- Modify: `vm-unified/src/components/layout/navigation-panel.tsx`

**Step 1: Substituir mock data pelos hooks reais**

Modify: `vm-unified/src/components/layout/navigation-panel.tsx`

```typescript
import { ChevronDown, ChevronRight, Plus, MoreHorizontal, Loader2 } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { useBrands } from '@/hooks/api/use-brands'
import { useProjects } from '@/hooks/api/use-projects'
import { useThreads } from '@/hooks/api/use-threads'
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

## Task 11: Integrar no CommandRail

**Files:**
- Modify: `vm-unified/src/components/layout/command-rail.tsx`

**Step 1: Integrar useRuns**

Modify: `vm-unified/src/components/layout/command-rail.tsx`

```typescript
import { Command, Play, CheckCircle, RotateCcw, Loader2 } from 'lucide-react'
import { useStore } from '@/hooks/use-store'
import { useRuns, useResumeRun } from '@/hooks/api/use-runs'
import { Kbd } from '@/components/ui/kbd'
import { cn } from '@/lib/utils'

export function CommandRail() {
  const { activeThreadId, activeRunId } = useStore()
  const { data: runs = [], isLoading } = useRuns(activeThreadId)
  const activeRun = runs.find(r => r.id === activeRunId)
  const resumeRun = useResumeRun()

  return (
    <div className="h-full flex flex-col bg-vm-surface border-l border-vm-border">
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
                onClick={() => activeRun && resumeRun.mutate({ runId: activeRun.id, threadId: activeThreadId! })}
                isLoading={resumeRun.isPending}
              />
              <CommandItem icon={CheckCircle} label="Approve Stage" />
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
git commit -m "feat(vm-unified): integrate useRuns into CommandRail"
```

---

## Task 12: Adicionar Toast Container ao App

**Files:**
- Modify: `vm-unified/src/app/App.tsx`

**Step 1: Adicionar ToastContainer e provider de toast**

Modify: `vm-unified/src/app/App.tsx`

```typescript
import { Header } from '@/components/layout/header'
import { NavigationPanel } from '@/components/layout/navigation-panel'
import { Workspace } from '@/components/layout/workspace'
import { CommandRail } from '@/components/layout/command-rail'
import { ToastContainer } from '@/components/ui/toast-container'
import { useKeyboard } from '@/hooks/use-keyboard'
import { useToast } from '@/hooks/ui/use-toast'

function App() {
  useKeyboard()
  const { toasts, removeToast } = useToast()

  return (
    <div className="h-screen flex flex-col bg-vm-bg">
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <aside className="w-64 border-r border-vm-border bg-vm-bg shrink-0" data-panel="navigation">
          <NavigationPanel />
        </aside>
        <main className="flex-1 min-w-0 bg-vm-bg" data-panel="workspace">
          <Workspace />
        </main>
        <aside className="w-72 shrink-0" data-panel="command">
          <CommandRail />
        </aside>
      </div>
    </div>
  )
}

export default App
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/app/App.tsx
git commit -m "feat(vm-unified): add ToastContainer to App"
```

---

## Task 13: Remover Mock Data do Store

**Files:**
- Modify: `vm-unified/src/hooks/use-store.ts`

**Step 1: Limpar store para conter apenas UI state**

Modify: `vm-unified/src/hooks/use-store.ts`

Remover:
- `mockBrands`, `mockProjects`, `mockThreads`, `mockRuns`, `mockArtifacts`
- Valores iniciais de `brands`, `projects`, etc. devem ser arrays vazios
- `activeBrandId: 'brand-1'` → `activeBrandId: null`
- `activeProjectId: 'proj-1'` → `activeProjectId: null`
- `activeThreadId: 'thread-1'` → `activeThreadId: null`
- `activeRunId: 'run-1'` → `activeRunId: null`

```typescript
// Initial State (limpo, sem mocks)
brands: [],
projects: [],
threads: [],
runs: [],
artifacts: [],

activeBrandId: null,
activeProjectId: null,
activeThreadId: null,
activeRunId: null,
```

**Step 2: Commit**

```bash
git add 09-tools/web/vm-unified/src/hooks/use-store.ts
git commit -m "refactor(vm-unified): remove mock data from store"
```

---

## Task 14: Testar Integração

**Step 1: Subir backend**

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools
uv run python -m vm_webapp serve --host 127.0.0.1 --port 8766
```

**Step 2: Subir frontend**

```bash
cd /Users/jhonatan/Repos/marketing-skills/09-tools/web/vm-unified
npm run dev
```

**Step 3: Verificar funcionalidades**

Abrir http://localhost:5173 e testar:
- [ ] Lista de brands carrega
- [ ] Expandir brand carrega projects
- [ ] Expandir project carrega threads
- [ ] Selecionar thread carrega runs
- [ ] Polling funciona quando run está em "running"
- [ ] Toast aparece em erros

**Step 4: Commit final**

```bash
git commit --allow-empty -m "test(vm-unified): verify API integration complete"
```

---

## Resumo

Este plano implementa:

1. React Query setup
2. API client base (GET, POST, PATCH, DELETE + idempotency)
3. Backend types (snake_case)
4. Adapters (map/unmap)
5. Toast system
6. useBrands (Full CRUD)
7. useProjects (Full CRUD)
8. useThreads (Full CRUD)
9. useRuns (com polling)
10. Integração NavigationPanel
11. Integração CommandRail
12. Toast Container
13. Limpeza de mock data
14. Testes

**Total:** 14 tasks
