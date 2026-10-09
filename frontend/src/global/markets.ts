import type { Language } from '../i18n'
import type { Currency } from './currency'

export type MarketId = 'jp' | 'hk' | 'us'
export type Tab = 'global' | MarketId

export const MARKETS: Record<MarketId, { currency: Currency; flag: string }> = {
  jp: { currency: 'JPY', flag: '🇯🇵' },
  hk: { currency: 'HKD', flag: '🇭🇰' },
  us: { currency: 'USD', flag: '🇺🇸' },
}

export function parseTab(value: string | null): Tab {
  return value === 'jp' || value === 'hk' || value === 'us' ? value : 'global'
}

export function tabCurrency(tab: Tab): Currency {
  return tab === 'global' ? 'JPY' : MARKETS[tab].currency
}

export const CAPACITY_ORDER = ['64', '128', '256', '512', '1TB', '2TB']
export const ALL_COLORS = 'all'

export interface ColorInfo {
  hex: string
  name: Record<Language, string>
}

export const COLORS: Record<string, ColorInfo> = {
  black: { hex: '#1f2023', name: { ja: 'ブラック', zh: '黑色', en: 'Black' } },
  silver: { hex: '#dfe1e4', name: { ja: 'シルバー', zh: '银色', en: 'Silver' } },
  glacier: { hex: '#a9c6df', name: { ja: 'グレイシャー', zh: '冰川色', en: 'Glacier' } },
  burgundy: { hex: '#6b2632', name: { ja: 'バーガンディ', zh: '布根地红', en: 'Burgundy' } },
}

/** Prices of one model in one market, in that market's currency. */
export interface MarketBoard {
  market: MarketId
  currency: Currency
  model: string
  colors: string[] // [ALL_COLORS] when the market does not price colours separately
  official: Record<string, number | null>
  prices: Record<string, Record<string, number>> // capacity -> colour -> price
  storeCount?: Record<string, number>
  sample: boolean
}

export function modelSlug(model: string) {
  return model.toLowerCase().replace(/\s+/g, '-')
}

export function capacityLabel(capacity: string) {
  return /^\d+$/.test(capacity) ? `${capacity}GB` : capacity
}

export function sortCapacities(capacities: string[]) {
  return [...capacities].sort((a, b) => CAPACITY_ORDER.indexOf(a) - CAPACITY_ORDER.indexOf(b))
}

export function bestPrice(board: MarketBoard, capacity: string) {
  const values = Object.values(board.prices[capacity] ?? {})
  return values.length ? Math.max(...values) : null
}

// ---------------------------------------------------------------------------
// Sample data for Hong Kong and the United States, shown with a "sample" badge
// until collection for these markets exists. Hong Kong iPhone 18 Pro follows a
// Sin Tat Plaza price board; other values are illustrative.
// ---------------------------------------------------------------------------

const PRO_COLORS = ['black', 'silver', 'glacier', 'burgundy']

function hkBoard(model: string, official: Record<string, number>, rows: Record<string, number[]>): MarketBoard {
  const prices: MarketBoard['prices'] = {}
  for (const [capacity, values] of Object.entries(rows)) {
    prices[capacity] = Object.fromEntries(PRO_COLORS.map((color, index) => [color, values[index]]))
  }
  return { market: 'hk', currency: 'HKD', model, colors: PRO_COLORS, official, prices, sample: true }
}

function usBoard(model: string, official: Record<string, number>, rows: Record<string, number>): MarketBoard {
  const prices: MarketBoard['prices'] = {}
  for (const [capacity, value] of Object.entries(rows)) prices[capacity] = { [ALL_COLORS]: value }
  return { market: 'us', currency: 'USD', model, colors: [ALL_COLORS], official, prices, sample: true }
}

export const SAMPLE_BOARDS: MarketBoard[] = [
  hkBoard(
    'iPhone 18 Pro',
    { '256': 10499, '512': 12299, '1TB': 15799, '2TB': 20999 },
    {
      '256': [9800, 9600, 9620, 9850],
      '512': [11760, 11300, 11300, 11720],
      '1TB': [15400, 15400, 15350, 15400],
      '2TB': [19000, 19000, 19000, 19000],
    },
  ),
  hkBoard(
    'iPhone 18 Pro Max',
    { '256': 11299, '512': 13099, '1TB': 16599, '2TB': 21799 },
    {
      '256': [11800, 11750, 11760, 11840],
      '512': [13400, 13250, 13300, 13450],
      '1TB': [16500, 16450, 16450, 16500],
      '2TB': [20500, 20500, 20500, 20500],
    },
  ),
  usBoard('iPhone 18 Pro', { '256': 1099, '512': 1299, '1TB': 1499, '2TB': 1899 }, { '256': 900, '512': 1010, '1TB': 1150, '2TB': 1420 }),
  usBoard('iPhone 18 Pro Max', { '256': 1199, '512': 1399, '1TB': 1599, '2TB': 1999 }, { '256': 1070, '512': 1180, '1TB': 1320, '2TB': 1640 }),
]

// ---------------------------------------------------------------------------
// Japan: real data from the public price list (best price per model/capacity).
// ---------------------------------------------------------------------------

export interface PublicPrice {
  price: number
  store: { id: number } | null
  product: { model: string; capacity: string | null; retail_price: number | null } | null
}

export function japanBoards(prices: PublicPrice[]): MarketBoard[] {
  const boards = new Map<string, MarketBoard>()
  const stores = new Map<string, Set<number>>()
  for (const row of prices) {
    const model = row.product?.model
    const capacity = row.product?.capacity
    if (!model || !capacity || !model.startsWith('iPhone')) continue
    let board = boards.get(model)
    if (!board) {
      board = { market: 'jp', currency: 'JPY', model, colors: [ALL_COLORS], official: {}, prices: {}, storeCount: {}, sample: false }
      boards.set(model, board)
    }
    const current = board.prices[capacity]?.[ALL_COLORS] ?? 0
    board.prices[capacity] = { [ALL_COLORS]: Math.max(current, row.price) }
    board.official[capacity] = row.product?.retail_price ?? board.official[capacity] ?? null
    const key = `${model}|${capacity}`
    if (!stores.has(key)) stores.set(key, new Set())
    if (row.store) stores.get(key)!.add(row.store.id)
    board.storeCount![capacity] = stores.get(key)!.size
  }
  return [...boards.values()]
}

/** Newest generation and bigger variants first. */
export function compareModels(a: string, b: string) {
  const generation = (model: string) => Number(model.match(/iPhone (\d+)/)?.[1] ?? 0)
  const rank = (model: string) => (/Pro Max/.test(model) ? 0 : /Pro/.test(model) ? 1 : /Air/.test(model) ? 2 : /Plus/.test(model) ? 3 : /e$/.test(model) ? 5 : 4)
  return generation(b) - generation(a) || rank(a) - rank(b) || a.localeCompare(b)
}
