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
