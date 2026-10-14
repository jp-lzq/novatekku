import { useQuery } from '@tanstack/react-query'
import { apiGet } from '../lib/api'
import { compareModels, japanBoards, overseasBoards, type ColorName, type ColorPriceRow, type MarketBoard, type MarketId, type MarketPriceResponse } from './markets'

export type ModelBoards = { model: string } & Partial<Record<MarketId, MarketBoard>>

const market = (id: 'hk' | 'us') => ({
  queryKey: ['prices', 'markets', id],
  queryFn: () => apiGet<MarketPriceResponse>('/api/v1/prices/markets', { params: { market: id } }),
  staleTime: 60_000,
})

/** All boards grouped by model: Japan, Hong Kong and the US, all from live data. */
export function useGlobalBoards() {
  const japan = useQuery<{ products: ColorPriceRow[] }>({
    queryKey: ['prices', 'colors'],
    queryFn: () => apiGet<{ products: ColorPriceRow[] }>('/api/v1/prices/colors'),
    staleTime: 60_000,
  })
  const hk = useQuery<MarketPriceResponse>(market('hk'))
  const us = useQuery<MarketPriceResponse>(market('us'))

  const names = new Map<string, ColorName>()
  for (const row of japan.data?.products ?? []) {
    for (const color of row.colors) names.set(`${row.model}|${color.code}`, { ja: color.name_ja, en: color.name_en, zh: color.name_zh })
  }
  const boards: MarketBoard[] = [
    ...japanBoards(japan.data?.products ?? []),
    ...(hk.data ? overseasBoards(hk.data, names) : []),
    ...(us.data ? overseasBoards(us.data, names) : []),
  ]
  const byModel = new Map<string, ModelBoards>()
  for (const board of boards) {
    const entry = byModel.get(board.model) ?? { model: board.model }
    entry[board.market] = board
    byModel.set(board.model, entry)
  }
  const models = [...byModel.values()].sort((a, b) => compareModels(a.model, b.model))
  return {
    models,
    updated: { jp: null as string | null, hk: hk.data?.updated_at ?? null, us: us.data?.updated_at ?? null },
    isLoading: japan.isLoading || hk.isLoading || us.isLoading,
    isError: japan.isError,
  }
}
