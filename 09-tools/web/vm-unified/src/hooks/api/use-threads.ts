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
  const { success, error: toastError } = useToast()

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
      success(`Thread "${newThread.name}" created`)
    },
    onError: (error: Error) => {
      toastError('Failed to create thread', error.message)
    },
  })
}

export function useUpdateThread() {
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()

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
      await queryClient.cancelQueries({ queryKey: [THREADS_KEY, projectId] })
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
      toastError('Failed to update thread')
    },
    onSettled: (data) => {
      queryClient.invalidateQueries({ queryKey: [THREADS_KEY, data?.projectId] })
    },
  })
}

export function useDeleteThread() {
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()

  return useMutation({
    mutationFn: async ({ id, projectId }: { id: string; projectId: string }) => {
      await del(`/threads/${id}`, buildIdempotencyKey(`thread-delete-${id}`))
      return { id, projectId }
    },
    onMutate: async ({ id, projectId }) => {
      await queryClient.cancelQueries({ queryKey: [THREADS_KEY, projectId] })
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
      toastError('Failed to delete thread')
    },
    onSettled: (data) => {
      queryClient.invalidateQueries({ queryKey: [THREADS_KEY, data?.projectId] })
    },
    onSuccess: () => {
      success('Thread deleted')
    },
  })
}
