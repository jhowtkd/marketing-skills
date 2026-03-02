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
