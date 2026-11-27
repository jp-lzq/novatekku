import { useQuery } from '@tanstack/react-query'
import { apiGet } from '../lib/api'
import type { Currency } from './currency'
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

export interface MarketStoreResponse {
  market: 'hk' | 'us'
  currency: 'HKD' | 'USD'
  updated_at: string | null
  products: { model: string; capacity: string; color_code: string | null; stores: { store: string; price: number; collected_at: string }[] }[]
}

/** Prices per store for one overseas market (the US lists every buyer; Hong Kong is one store, "香港"). */
export function useMarketStores(market: 'hk' | 'us', enabled: boolean) {
  return useQuery<MarketStoreResponse>({
    queryKey: ['prices', 'market-stores', market],
    queryFn: () => apiGet<MarketStoreResponse>('/api/v1/prices/market-stores', { params: { market } }),
    staleTime: 60_000,
    enabled,
  })
}

export type SellAdvice = 'japan_best' | 'overseas_small' | 'overseas_clear' | 'japan_only'

export interface WhereToSellStore {
  store: string
  price: number
  currency: Currency
  price_jpy: number | null
}

export interface WhereToSellMarket {
  market: MarketId
  price: number
  currency: Currency
  price_jpy: number
  store: string | null
  buyers: number | null
  rank: number
  behind_top: number
  stores: WhereToSellStore[]
}

export interface WhereToSellResponse {
  model: string
  capacity: string | null
  capacities: string[]
  markets: WhereToSellMarket[]
  advice: SellAdvice | null
  best_market: MarketId | null
  best_overseas_market: 'hk' | 'us' | null
  overseas_gap: number | null
  overseas_gap_percent: number | null
  small_gap_percent: number
  japan_direction: 'up' | 'down' | 'flat' | null
  japan_change_7d: { change: number; percent: number; from_date: string } | null
  fx: { rates: Partial<Record<'HKD' | 'USD', number | null>>; updated_at: string | null }
  updated_at: Record<MarketId, string | null>
}

/**
 * Where one phone sells best: Japan, Hong Kong and the US ranked in yen with a recommendation.
 * Without a capacity the server picks the smallest quoted one; an unknown model is an error (no card).
 */
export function useWhereToSell(model: string | undefined, capacity?: string | null) {
  return useQuery<WhereToSellResponse>({
    queryKey: ['prices', 'where-to-sell', model, capacity ?? null],
    queryFn: () => apiGet<WhereToSellResponse>('/api/v1/prices/where-to-sell', { params: { model, ...(capacity ? { capacity } : {}) } }),
    staleTime: 60_000,
    enabled: Boolean(model),
    retry: false,
    placeholderData: (previous) => (previous?.model === model ? previous : undefined), // keep the card while another capacity loads
  })
}
