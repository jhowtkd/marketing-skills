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
  const { success, error: toastError } = useToast()

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
      success(`Project "${newProject.name}" created`)
    },
    onError: (error: Error) => {
      toastError('Failed to create project', error.message)
    },
  })
}

export function useUpdateProject() {
  const queryClient = useQueryClient()
  const { error: toastError } = useToast()

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
      await queryClient.cancelQueries({ queryKey: [PROJECTS_KEY, brandId] })
      const previous = queryClient.getQueryData<Project[]>([PROJECTS_KEY, brandId])
      
      queryClient.setQueryData([PROJECTS_KEY, brandId], (old: Project[] = []) =>
        old.map(p => p.id === id ? { ...p, ...updates, updatedAt: new Date().toISOString() } : p)
      )
      
      return { previous }
    },
    onError: (_err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([PROJECTS_KEY, vars.updates.brandId], context.previous)
      }
      toastError('Failed to update project')
    },
    onSettled: (data) => {
      queryClient.invalidateQueries({ queryKey: [PROJECTS_KEY, data?.brandId] })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()

  return useMutation({
    mutationFn: async ({ id, brandId }: { id: string; brandId: string }) => {
      await del(`/projects/${id}`, buildIdempotencyKey(`project-delete-${id}`))
      return { id, brandId }
    },
    onMutate: async ({ id, brandId }) => {
      await queryClient.cancelQueries({ queryKey: [PROJECTS_KEY, brandId] })
      const previous = queryClient.getQueryData<Project[]>([PROJECTS_KEY, brandId])
      
      queryClient.setQueryData([PROJECTS_KEY, brandId], (old: Project[] = []) =>
        old.filter(p => p.id !== id)
      )
      
      return { previous }
    },
    onError: (_err, vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([PROJECTS_KEY, vars.brandId], context.previous)
      }
      toastError('Failed to delete project')
    },
    onSettled: (data) => {
      queryClient.invalidateQueries({ queryKey: [PROJECTS_KEY, data?.brandId] })
    },
    onSuccess: () => {
      success('Project deleted')
    },
  })
}
