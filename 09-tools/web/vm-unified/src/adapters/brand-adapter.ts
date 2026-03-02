import type { BrandResponse } from '@/types/api'
import type { Brand } from '@/types'

export function mapBrand(response: BrandResponse): Brand {
  const now = new Date().toISOString()
  return {
    id: response.brand_id,
    name: response.name,
    createdAt: now,
    updatedAt: now,
  }
}

export function unmapBrand(brand: Partial<Brand>): { brand_id?: string; name?: string } {
  return {
    brand_id: brand.id,
    name: brand.name,
  }
}
