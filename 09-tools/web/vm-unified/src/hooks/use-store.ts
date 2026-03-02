import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { Brand, Project, Thread, Run, Artifact, ViewMode, Template, ChatState } from '@/types'

// Mock data for development
const mockBrands: Brand[] = [
  { id: 'brand-1', name: 'Acme Corp', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'brand-2', name: 'TechStart', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
]

const mockProjects: Project[] = [
  { id: 'proj-1', brandId: 'brand-1', name: 'Q1 Launch', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'proj-2', brandId: 'brand-1', name: 'Product Hunt', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'proj-3', brandId: 'brand-2', name: 'Beta Campaign', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
]

const mockThreads: Thread[] = [
  { id: 'thread-1', projectId: 'proj-1', name: 'Landing Page', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'thread-2', projectId: 'proj-1', name: 'Email Sequence', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'thread-3', projectId: 'proj-2', name: 'PH Launch', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
]

const mockRuns: Run[] = [
  {
    id: 'run-1',
    threadId: 'thread-1',
    status: 'waiting_approval',
    currentStage: 'brand-voice',
    stages: [
      { key: 'research', name: 'Research', status: 'completed' },
      { key: 'brand-voice', name: 'Brand Voice', status: 'waiting_approval' },
      { key: 'positioning', name: 'Positioning', status: 'pending' },
      { key: 'keywords', name: 'Keywords', status: 'pending' },
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
]

const mockArtifacts: Artifact[] = [
  { path: '/research/market-landscape.md', name: 'market-landscape.md', type: 'markdown', stageKey: 'research', runId: 'run-1' },
  { path: '/research/competitor-gaps.md', name: 'competitor-gaps.md', type: 'markdown', stageKey: 'research', runId: 'run-1' },
]

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
      brands: mockBrands,
      projects: mockProjects,
      threads: mockThreads,
      runs: mockRuns,
      artifacts: mockArtifacts,

      activeBrandId: 'brand-1',
      activeProjectId: 'proj-1',
      activeThreadId: 'thread-1',
      activeRunId: 'run-1',

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
