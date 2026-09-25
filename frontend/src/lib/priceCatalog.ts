import { useQuery } from '@tanstack/react-query'
import { apiGet } from './api'

export interface ProductColor {
  name_ja: string
  name_en: string
  name_zh: string
}

export interface CatalogProduct {
  id: number
  name: string
  model: string
  capacity: string
  retail_price: number | null
  carrier?: string | null
  color?: string | null
  image_url?: string | null
  colors?: ProductColor[]
}

export function usePriceCatalog() {
  return useQuery<{ products: CatalogProduct[] }>({
    queryKey: ['price-catalog'],
    queryFn: () => apiGet('/api/v1/prices/assessment'),
    staleTime: 60_000,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
  })
}
