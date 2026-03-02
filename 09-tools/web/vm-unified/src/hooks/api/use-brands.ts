import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { get, post, patch, del, buildIdempotencyKey } from '@/lib/api'
import type { BrandResponse, BrandsResponse } from '@/types/api'
import type { Brand } from '@/types'
import { mapBrand, unmapBrand } from '@/adapters/brand-adapter'
import { useToast } from '@/hooks/ui/use-toast'

const BRANDS_KEY = 'brands'

// GET /brands
export function useBrands() {
  return useQuery({
    queryKey: [BRANDS_KEY],
    queryFn: async () => {
      const response = await get<BrandsResponse>('/brands')
      return response.brands.map(mapBrand)
    },
    staleTime: 5 * 60 * 1000,
  })
}

// POST /brands
export function useCreateBrand() {
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()

  return useMutation({
    mutationFn: async (name: string) => {
      const brandId = `brand-${Date.now().toString(36)}`
      const payload = unmapBrand({ id: brandId, name })
      
      const response = await post<BrandResponse>(
        '/brands',
        payload,
        buildIdempotencyKey('brand-create')
      )
      
      return mapBrand(response)
    },
    onSuccess: (newBrand) => {
      queryClient.setQueryData([BRANDS_KEY], (old: Brand[] = []) => [...old, newBrand])
      success(`Brand "${newBrand.name}" created`)
    },
    onError: (error: Error) => {
      toastError('Failed to create brand', error.message)
    },
  })
}

// PATCH /brands/:id
export function useUpdateBrand() {
  const queryClient = useQueryClient()
  const { error: toastError } = useToast()

  return useMutation({
    mutationFn: async ({ id, updates }: { id: string; updates: Partial<Brand> }) => {
      const payload = unmapBrand(updates)
      const response = await patch<BrandResponse>(
        `/brands/${id}`,
        payload,
        buildIdempotencyKey(`brand-update-${id}`)
      )
      return mapBrand(response)
    },
    onMutate: async ({ id, updates }) => {
      await queryClient.cancelQueries({ queryKey: [BRANDS_KEY] })
      const previous = queryClient.getQueryData<Brand[]>([BRANDS_KEY])
      
      queryClient.setQueryData([BRANDS_KEY], (old: Brand[] = []) =>
        old.map(b => b.id === id ? { ...b, ...updates, updatedAt: new Date().toISOString() } : b)
      )
      
      return { previous }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData([BRANDS_KEY], context.previous)
      }
      toastError('Failed to update brand')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [BRANDS_KEY] })
    },
  })
}

// DELETE /brands/:id
export function useDeleteBrand() {
  const queryClient = useQueryClient()
  const { success, error: toastError } = useToast()

  return useMutation({
    mutationFn: async (brandId: string) => {
      await del(`/brands/${brandId}`, buildIdempotencyKey(`brand-delete-${brandId}`))
      return brandId
    },
    onMutate: async (brandId) => {
      await queryClient.cancelQueries({ queryKey: [BRANDS_KEY] })
      const previous = queryClient.getQueryData<Brand[]>([BRANDS_KEY])
      
      queryClient.setQueryData([BRANDS_KEY], (old: Brand[] = []) =>
        old.filter(b => b.id !== brandId)
      )
      
      return { previous }
    },
    onError: (_err, _brandId, context) => {
      if (context?.previous) {
        queryClient.setQueryData([BRANDS_KEY], context.previous)
      }
      toastError('Failed to delete brand')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: [BRANDS_KEY] })
    },
    onSuccess: () => {
      success('Brand deleted')
    },
  })
}
