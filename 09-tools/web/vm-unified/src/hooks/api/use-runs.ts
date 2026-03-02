import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, buildIdempotencyKey } from '@/lib/api'
import type { RunsResponse } from '@/types/api'
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
    
    refetchInterval: (query) => {
      const data = query.state.data
      const hasRunning = data?.some((run: { status: string }) => 
        run.status === 'running' || run.status === 'queued'
      )
      return hasRunning ? 2000 : false
    },
    
    retry: (failureCount, error) => {
      const status = (error as unknown as { status?: number }).status
      if (status && status >= 500) return failureCount < 3
      return false
    },
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
  })
}

export function useCreateRun() {
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()

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
      success('Workflow started')
      queryClient.invalidateQueries({ queryKey: [RUNS_KEY, variables.threadId] })
    },
    onError: (error: Error) => {
      toastError('Failed to start workflow', error.message)
    },
  })
}

export function useResumeRun() {
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()

  return useMutation({
    mutationFn: async ({ runId }: { runId: string; threadId: string }) => {
      const response = await post<{ run_id: string; status: string }>(
        `/workflow-runs/${encodeURIComponent(runId)}/resume`,
        {},
        buildIdempotencyKey(`run-resume-${runId}`)
      )
      return response
    },
    onSuccess: (_, variables) => {
      success('Workflow resumed')
      queryClient.invalidateQueries({ queryKey: [RUNS_KEY, variables.threadId] })
    },
    onError: (error: Error) => {
      toastError('Failed to resume workflow', error.message)
    },
  })
}

export function useGrantApproval() {
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()

  return useMutation({
    mutationFn: async ({ approvalId }: { approvalId: string; threadId: string }) => {
      await post(
        `/approvals/${encodeURIComponent(approvalId)}/grant`,
        {},
        buildIdempotencyKey(`approval-grant-${approvalId}`)
      )
    },
    onSuccess: (_, variables) => {
      success('Stage approved')
      queryClient.invalidateQueries({ queryKey: [RUNS_KEY, variables.threadId] })
    },
    onError: (error: Error) => {
      toastError('Failed to approve', error.message)
    },
  })
}
