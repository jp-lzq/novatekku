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

/** Official finish colours (approximate hex) keyed by the catalogue colour code. */
export const COLOR_HEX: Record<string, string> = {
  black: '#232427', silver: '#e2e3e1', glacier: '#b7cee0', burgundy: '#6a2433',
  white: '#f2f1ec', 'soft-pink': '#efd5d4',
  'deep-blue': '#2e3b55', 'cosmic-orange': '#e2763a',
  'space-black': '#26262a', 'cloud-white': '#f3f2ee', 'light-gold': '#e8dabf', 'sky-blue': '#bcd3e6',
  'mist-blue': '#a8bcd1', sage: '#b3bea2', lavender: '#c8bee0',
  'black-titanium': '#3a3a3c', 'white-titanium': '#e7e5e0', 'natural-titanium': '#b7b2a7', 'desert-titanium': '#bea389',
  pink: '#f1c5cf', teal: '#8ec1bc', ultramarine: '#6976d5',
  'blue-titanium': '#3e4a5b', blue: '#cddae3', green: '#cfdbca', yellow: '#efe5b6',
  gold: '#f0e1c5', 'deep-purple': '#594a61', midnight: '#2b2f37', starlight: '#f1ebdf', purple: '#d6c8e3', 'product-red': '#c71f2e',
  'star-white': '#eceae4', 'night-sky': '#1e2738',
}

export type ColorName = Record<Language, string>

export interface MarketColor {
  code: string
  name: ColorName
}

/** Prices of one model in one market, in that market's currency. */
export interface MarketBoard {
  market: MarketId
  currency: Currency
  model: string
  colors: MarketColor[]
  official: Record<string, number | null>
  prices: Record<string, Record<string, number>> // capacity -> colour code -> price
  storeCount?: Record<string, Record<string, number>>
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

/** Smallest capacity and its best price, used for list summaries. */
export function basePrice(board: MarketBoard) {
  const capacity = sortCapacities(Object.keys(board.prices))[0]
  return capacity ? { capacity, price: bestPrice(board, capacity) } : null
}

/** Camera / body layout used to draw each model. */
export type PhoneShape = 'fold' | 'plateau' | 'air' | 'pill' | 'proTriple' | 'diagonal' | 'single'

export function phoneShape(model: string): PhoneShape {
  if (/Duo/.test(model)) return 'fold'
  if (/^iPhone 1[78] Pro/.test(model)) return 'plateau'
  if (/Air/.test(model)) return 'air'
  if (/1[67]e$/.test(model)) return 'single'
  if (/^iPhone 1[456] Pro/.test(model)) return 'proTriple'
  if (/^iPhone 1[67]/.test(model)) return 'pill'
  return 'diagonal'
}

export function isLarge(model: string) {
  return /Max|Plus/.test(model)
}

/** Newest generation and bigger variants first. */
export function compareModels(a: string, b: string) {
  const generation = generationOf
  const rank = (model: string) => (/Duo/.test(model) ? -1 : /Pro Max/.test(model) ? 0 : /Pro/.test(model) ? 1 : /Air/.test(model) ? 2 : /Plus/.test(model) ? 3 : /e$/.test(model) ? 5 : 4)
  return generation(b) - generation(a) || rank(a) - rank(b) || a.localeCompare(b)
}

// ---------------------------------------------------------------------------
// Japan: live best price per model / capacity / colour from /api/v1/prices/colors.
// ---------------------------------------------------------------------------

export const ALL_COLORS = 'all'
export const ALL_COLORS_NAME: ColorName = { ja: '全色共通', zh: '全色通用', en: 'All colors' }

export interface ColorPriceRow {
  model: string
  capacity: string
  retail_price: number | null
  colors: { code: string; name_ja: string; name_en: string; name_zh: string; price: number | null; store_count: number }[]
  all_colors?: { price: number; store_count: number } | null // stores quoting one price for every colour
}

export function japanBoards(rows: ColorPriceRow[]): MarketBoard[] {
  const boards = new Map<string, MarketBoard>()
  for (const row of rows) {
    if (!row.model.startsWith('iPhone') || !row.capacity) continue
    let board = boards.get(row.model)
    if (!board) {
      board = { market: 'jp', currency: 'JPY', model: row.model, colors: [], official: {}, prices: {}, storeCount: {}, sample: false }
      boards.set(row.model, board)
    }
    board.official[row.capacity] = row.retail_price
    board.prices[row.capacity] = {}
    board.storeCount![row.capacity] = {}
    for (const color of row.colors) {
      if (!board.colors.some((item) => item.code === color.code)) {
        board.colors.push({ code: color.code, name: { ja: color.name_ja, en: color.name_en, zh: color.name_zh } })
      }
      if (color.price != null) {
        board.prices[row.capacity][color.code] = color.price
        board.storeCount![row.capacity][color.code] = color.store_count
      }
    }
    if (row.all_colors) {
      board.prices[row.capacity][ALL_COLORS] = row.all_colors.price
      board.storeCount![row.capacity][ALL_COLORS] = row.all_colors.store_count
    }
  }
  // colour columns first, then one "all colours" column when any store quotes a single price
  for (const board of boards.values()) {
    if (Object.values(board.prices).some((cells) => ALL_COLORS in cells)) {
      board.colors.push({ code: ALL_COLORS, name: ALL_COLORS_NAME })
    }
  }
  return [...boards.values()]
}

// ---------------------------------------------------------------------------
// Hong Kong / United States: live data from /api/v1/prices/markets.
// ---------------------------------------------------------------------------

export interface MarketPriceResponse {
  market: 'hk' | 'us'
  currency: Currency
  updated_at: string | null
  products: { model: string; capacity: string; official_price: number | null; colors: { code: string | null; price: number; store_count: number }[] }[]
}

/** Colour names come from the Japanese catalogue of the same model; unknown codes are title-cased. */
export function overseasBoards(response: MarketPriceResponse, names: Map<string, ColorName>): MarketBoard[] {
  const order_ = new Map([...names.keys()].map((key, index) => [key, index]))
  const boards = new Map<string, MarketBoard>()
  for (const row of response.products) {
    let board = boards.get(row.model)
    if (!board) {
      board = { market: response.market, currency: response.currency, model: row.model, colors: [], official: {}, prices: {}, storeCount: {}, sample: false }
      boards.set(row.model, board)
    }
    board.official[row.capacity] = row.official_price
    board.prices[row.capacity] = {}
    board.storeCount![row.capacity] = {}
    for (const color of row.colors) {
      const code = color.code ?? ALL_COLORS
      if (!board.colors.some((item) => item.code === code)) {
        const fallback = code.replace(/(^|-)(\w)/g, (_m, dash: string, ch: string) => (dash ? ' ' : '') + ch.toUpperCase())
        const name = code === ALL_COLORS ? null : names.get(`${row.model}|${code}`)
        board.colors.push({ code, name: code === ALL_COLORS ? ALL_COLORS_NAME : name ?? { ja: fallback, zh: fallback, en: fallback } })
      }
      board.prices[row.capacity][code] = color.price
      board.storeCount![row.capacity][code] = color.store_count
    }
  }
  // same colour order as the Japanese catalogue (black, silver, glacier, burgundy, ...)
  for (const board of boards.values()) {
    const order = (code: string) => {
      const index = order_.get(`${board.model}|${code}`)
      return index === undefined ? 999 : index
    }
    board.colors.sort((a, b) => order(a.code) - order(b.code))
  }
  return [...boards.values()]
}

/** Generation number used to group the model list ("iPhone 17 Air" → 17). */
export function generationOf(model: string) {
  if (/iPhone Duo/.test(model)) return 18 // the foldable launched with the 18 series
  return Number(model.match(/iPhone (\d+)/)?.[1] ?? 0)
}
