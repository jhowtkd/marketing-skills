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
