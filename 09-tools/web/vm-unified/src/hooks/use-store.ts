import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Brand, Project, Thread, Run, Artifact, ViewMode, Template, ChatState } from '@/types'

interface VMState {
  // Hierarchy
  brands: Brand[]
  projects: Project[]
  threads: Thread[]
  runs: Run[]
  artifacts: Artifact[]

  // Selection
  activeBrandId: string | null
  activeProjectId: string | null
  activeThreadId: string | null
  activeRunId: string | null

  // UI State
  viewMode: ViewMode
  chat: ChatState

  // Actions - Hierarchy
  setBrands: (brands: Brand[]) => void
  setProjects: (projects: Project[]) => void
  setThreads: (threads: Thread[]) => void
  setRuns: (runs: Run[]) => void
  setArtifacts: (artifacts: Artifact[]) => void

  // Actions - Selection
  selectBrand: (brandId: string | null) => void
  selectProject: (projectId: string | null) => void
  selectThread: (threadId: string | null) => void
  selectRun: (runId: string | null) => void

  // Actions - UI
  setViewMode: (mode: ViewMode) => void
  toggleViewMode: () => void
  setChatRequest: (request: string) => void
  setChatSuggestions: (suggestions: Template[]) => void
  setChatGenerating: (isGenerating: boolean) => void

  // Computed
  getActiveBrand: () => Brand | undefined
  getActiveProject: () => Project | undefined
  getActiveThread: () => Thread | undefined
  getActiveRun: () => Run | undefined
  getActiveArtifacts: () => Artifact[]
}

export const useStore = create<VMState>()(
  devtools(
    (set, get) => ({
      // Initial State
      brands: [],
      projects: [],
      threads: [],
      runs: [],
      artifacts: [],

      activeBrandId: null,
      activeProjectId: null,
      activeThreadId: null,
      activeRunId: null,

      viewMode: 'guided',
      chat: {
        request: '',
        suggestions: [],
        isGenerating: false,
      },

      // Actions - Hierarchy
      setBrands: (brands) => set({ brands }),
      setProjects: (projects) => set({ projects }),
      setThreads: (threads) => set({ threads }),
      setRuns: (runs) => set({ runs }),
      setArtifacts: (artifacts) => set({ artifacts }),

      // Actions - Selection
      selectBrand: (brandId) => set({
        activeBrandId: brandId,
        activeProjectId: null,
        activeThreadId: null,
        activeRunId: null,
      }),

      selectProject: (projectId) => set({
        activeProjectId: projectId,
        activeThreadId: null,
        activeRunId: null,
      }),

      selectThread: (threadId) => set({
        activeThreadId: threadId,
        activeRunId: null,
      }),

      selectRun: (runId) => set({ activeRunId: runId }),

      // Actions - UI
      setViewMode: (mode) => set({ viewMode: mode }),

      toggleViewMode: () => set((state) => ({
        viewMode: state.viewMode === 'guided' ? 'dev' : 'guided'
      })),

      setChatRequest: (request) => set((state) => ({
        chat: { ...state.chat, request }
      })),

      setChatSuggestions: (suggestions) => set((state) => ({
        chat: { ...state.chat, suggestions }
      })),

      setChatGenerating: (isGenerating) => set((state) => ({
        chat: { ...state.chat, isGenerating }
      })),

      // Computed
      getActiveBrand: () => {
        const { brands, activeBrandId } = get()
        return brands.find(b => b.id === activeBrandId)
      },

      getActiveProject: () => {
        const { projects, activeProjectId } = get()
        return projects.find(p => p.id === activeProjectId)
      },

      getActiveThread: () => {
        const { threads, activeThreadId } = get()
        return threads.find(t => t.id === activeThreadId)
      },

      getActiveRun: () => {
        const { runs, activeRunId } = get()
        return runs.find(r => r.id === activeRunId)
      },

      getActiveArtifacts: () => {
        const { artifacts, activeRunId } = get()
        return artifacts.filter(a => a.runId === activeRunId)
      },
    }),
    { name: 'VMStore' }
  )
)
