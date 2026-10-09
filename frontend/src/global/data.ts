import { useQuery } from '@tanstack/react-query'
import { apiGet } from '../lib/api'
import { SAMPLE_BOARDS, compareModels, japanBoards, type MarketBoard, type MarketId, type PublicPrice } from './markets'

export type ModelBoards = { model: string } & Partial<Record<MarketId, MarketBoard>>

/** All boards grouped by model: Japan from the live price list, Hong Kong / US samples. */
export function useGlobalBoards() {
  const query = useQuery<PublicPrice[]>({
    queryKey: ['prices'],
    queryFn: () => apiGet<PublicPrice[]>('/api/v1/prices'),
    staleTime: 60_000,
  })
  const byModel = new Map<string, ModelBoards>()
  for (const board of [...japanBoards(query.data ?? []), ...SAMPLE_BOARDS]) {
    const entry = byModel.get(board.model) ?? { model: board.model }
    entry[board.market] = board
    byModel.set(board.model, entry)
  }
  const models = [...byModel.values()].sort((a, b) => compareModels(a.model, b.model))
  return { models, isLoading: query.isLoading, isError: query.isError }
}
