// Hierarchy Types
export interface Brand {
  id: string
  name: string
  createdAt: string
  updatedAt: string
}

export interface Project {
  id: string
  brandId: string
  name: string
  objective?: string
  channels?: string[]
  dueDate?: string
  createdAt: string
  updatedAt: string
}

export interface Thread {
  id: string
  projectId: string
  brandId: string
  name: string
  status?: string
  modes?: string[]
  lastActivityAt?: string
  createdAt: string
  updatedAt: string
}

export interface Run {
  id: string
  threadId: string
  status: 'queued' | 'running' | 'waiting_approval' | 'completed' | 'failed'
  currentStage: string | null
  stages: Stage[]
  createdAt: string
  updatedAt: string
}

export interface Stage {
  key: string
  name: string
  status: 'pending' | 'running' | 'waiting_approval' | 'completed' | 'failed' | 'skipped'
  startedAt?: string
  completedAt?: string
}

export interface Artifact {
  path: string
  name: string
  type: 'markdown' | 'json' | 'yaml' | 'text'
  stageKey: string
  runId: string
}

// UI Types
export type ViewMode = 'guided' | 'dev'

export interface Template {
  id: string
  name: string
  description: string
  category: string
}

export interface ChatState {
  request: string
  suggestions: Template[]
  isGenerating: boolean
}
