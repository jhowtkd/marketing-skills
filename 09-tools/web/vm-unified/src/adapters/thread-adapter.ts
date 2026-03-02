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
