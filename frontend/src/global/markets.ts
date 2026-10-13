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
export type PhoneShape = 'plateau' | 'air' | 'pill' | 'proTriple' | 'diagonal' | 'single'

export function phoneShape(model: string): PhoneShape {
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
  const generation = (model: string) => Number(model.match(/iPhone (\d+)/)?.[1] ?? 0)
  const rank = (model: string) => (/Pro Max/.test(model) ? 0 : /Pro/.test(model) ? 1 : /Air/.test(model) ? 2 : /Plus/.test(model) ? 3 : /e$/.test(model) ? 5 : 4)
  return generation(b) - generation(a) || rank(a) - rank(b) || a.localeCompare(b)
}

// ---------------------------------------------------------------------------
// Japan: live best price per model / capacity / colour from /api/v1/prices/colors.
// ---------------------------------------------------------------------------

export interface ColorPriceRow {
  model: string
  capacity: string
  retail_price: number | null
  colors: { code: string; name_ja: string; name_en: string; name_zh: string; price: number; store_count: number }[]
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
      board.prices[row.capacity][color.code] = color.price
      board.storeCount![row.capacity][color.code] = color.store_count
    }
  }
  return [...boards.values()]
}

// ---------------------------------------------------------------------------
// Sample data for Hong Kong and the United States, shown with a "sample" badge
// until collection for these markets exists. Hong Kong iPhone 18 Pro follows a
// Sin Tat Plaza price board; other values are illustrative.
// ---------------------------------------------------------------------------

const PRO_18_COLORS: MarketColor[] = [
  { code: 'black', name: { ja: 'ブラック', zh: '黑色', en: 'Black' } },
  { code: 'silver', name: { ja: 'シルバー', zh: '银色', en: 'Silver' } },
  { code: 'glacier', name: { ja: 'グレイシャー', zh: '冰川蓝色', en: 'Glacier' } },
  { code: 'burgundy', name: { ja: 'バーガンディ', zh: '勃艮第酒红色', en: 'Burgundy' } },
]

function sampleBoard(market: 'hk' | 'us', model: string, official: Record<string, number>, rows: Record<string, number[]>): MarketBoard {
  const prices: MarketBoard['prices'] = {}
  for (const [capacity, values] of Object.entries(rows)) {
    prices[capacity] = Object.fromEntries(PRO_18_COLORS.map((color, index) => [color.code, values[index]]))
  }
  return { market, currency: MARKETS[market].currency, model, colors: PRO_18_COLORS, official, prices, sample: true }
}

export const SAMPLE_BOARDS: MarketBoard[] = [
  sampleBoard('hk', 'iPhone 18 Pro', { '256': 10499, '512': 12299, '1TB': 15799, '2TB': 20999 }, {
    '256': [9800, 9600, 9620, 9850],
    '512': [11760, 11300, 11300, 11720],
    '1TB': [15400, 15400, 15350, 15400],
    '2TB': [19000, 19000, 19000, 19000],
  }),
  sampleBoard('hk', 'iPhone 18 Pro Max', { '256': 11299, '512': 13099, '1TB': 16599, '2TB': 21799 }, {
    '256': [11800, 11750, 11760, 11840],
    '512': [13400, 13250, 13300, 13450],
    '1TB': [16500, 16450, 16450, 16500],
    '2TB': [20500, 20500, 20500, 20500],
  }),
  sampleBoard('us', 'iPhone 18 Pro', { '256': 1099, '512': 1299, '1TB': 1499, '2TB': 1899 }, {
    '256': [900, 885, 890, 905],
    '512': [1010, 995, 1000, 1015],
    '1TB': [1150, 1140, 1140, 1150],
    '2TB': [1420, 1420, 1410, 1420],
  }),
  sampleBoard('us', 'iPhone 18 Pro Max', { '256': 1199, '512': 1399, '1TB': 1599, '2TB': 1999 }, {
    '256': [1070, 1055, 1060, 1065],
    '512': [1180, 1170, 1175, 1185],
    '1TB': [1320, 1310, 1310, 1320],
    '2TB': [1640, 1640, 1630, 1640],
  }),
]
