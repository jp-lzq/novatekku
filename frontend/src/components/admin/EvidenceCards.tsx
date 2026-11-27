import { useState } from 'react'
import { ChevronDown, ChevronUp, Globe2, Palette, TrendingDown, TrendingUp, Minus } from 'lucide-react'

// The structured price evidence returned by /api/v1/ai/preview (see backend/app/ai_gateway/evidence).
// Only the fields shown here are typed; everything is optional because older evidence lacks newer blocks.

export interface RankEntry {
  store: string
  price: number
}

export interface Quotes {
  store_count?: number
  best_price?: number
  best_store?: string
  runner_up_price?: number | null
  lowest_price?: number
  median_price?: number
  spread?: number
  retail_price?: number | null
  best_vs_retail?: number | null
  best_vs_retail_percent?: number | null
  ranking?: RankEntry[]
  sponsored_stores?: string[]
}

export interface Change {
  change: number
  percent: number | null
  from_price?: number
}

export interface Trend {
  direction?: 'up' | 'down' | 'flat' | 'unknown'
  days_of_data?: number
  latest_price?: number
  high_30d?: number
  low_30d?: number
  change_7d?: Change | null
  change_30d?: Change | null
  slope_per_week?: number | null
}

export interface OverseasStore {
  store: string
  price: number
  currency: string
  price_jpy: number | null
}

export interface OverseasMarket {
  market: string
  price: number
  currency: string
  price_jpy: number | null
  buyers?: number
  vs_japan?: number
  vs_japan_percent?: number
  best_store?: string
  stores?: OverseasStore[]
}

export interface GlobalEntry {
  market: string
  price: number
  currency: string
  price_jpy: number
  store?: string | null
  rank: number
  behind_top: number
}

export interface GlobalComparison {
  ranking: GlobalEntry[]
  best_market: string
  advice: 'japan_best' | 'overseas_small' | 'overseas_clear' | 'japan_only'
  overseas_gap: number | null
  overseas_gap_percent: number | null
  spread: number
  japan_direction: 'up' | 'down' | 'flat' | null
}

export interface ColorQuote {
  code: string
  names: Record<string, string>
  best_price: number
  best_store: string
  store_count: number
  rank: number
  behind_top: number
}

export interface RequestedColor {
  code: string
  names: Record<string, string>
  quoted: boolean
  best_price?: number
  best_store?: string
  source?: 'color' | 'all_colors'
  behind_top?: number
}

export interface Colors {
  colors: ColorQuote[]
  all_colors: { best_price: number; best_store: string; store_count: number } | null
  top_color: string | null
  color_spread: number
  requested: RequestedColor | null
}

export interface CapacityEvidence {
  capacity: string
  quotes?: Quotes
  trend?: Trend
  overseas?: OverseasMarket[]
  global?: GlobalComparison | null
  colors?: Colors | null
}

export interface EvidenceItem {
  model: string
  requested_capacity?: string | null
  color?: string | null
  quantity?: number
  notes?: string[]
  capacities?: CapacityEvidence[]
}

export interface BulkLine {
  model: string
  capacity: string
  quantity: number
  store: string
  unit_price: number
  subtotal: number
}

export interface Bulk {
  total: number
  phones: number
  lines?: BulkLine[]
  single_store?: { store: string; total: number; difference?: number } | null
}

export interface StoreCompareLine {
  model: string
  capacity: string
  stores: { store: string; price: number; rank: number; behind_best: number }[]
  unquoted: string[]
  winner: string | null
  tie: boolean
  gap: number | null
  best_store: string | null
  best_price: number | null
  store_count: number
  best_is_asked: boolean
  gap_to_best: number | null
}

export interface TargetLine {
  model: string
  capacity: string
  target: number
  store_count: number
  reached: boolean
  reached_count: number
  stores: { store: string; price: number; over_target: number }[]
  best_price: number | null
  best_store: string | null
  best_vs_target: number | null
  shortfall: number | null
  direction: 'up' | 'down' | 'flat' | null
}

export interface PriceEvidence {
  has_prices?: boolean
  fx_updated?: string | null
  items?: EvidenceItem[]
  bulk?: Bulk | null
  store_compare?: { stores: string[]; items: StoreCompareLine[] } | null
  target_price?: { target: number; items: TargetLine[] } | null
}

const MARKET_LABELS: Record<string, string> = { jp: '日本', hk: '香港', us: 'アメリカ' }
const CURRENCY_SIGN: Record<string, string> = { JPY: '¥', HKD: 'HK$', USD: '$' }
const NOTE_LABELS: Record<string, string> = {
  unknown_model: '対象外の機種',
  no_prices: '価格なし',
  capacity_not_quoted: '指定容量の価格なし',
  capacity_missing: '容量の指定なし',
}
const ADVICE_LABELS: Record<GlobalComparison['advice'], { text: string; tone: string }> = {
  japan_best: { text: '日本で売るのが有利', tone: 'bg-emerald-50 text-emerald-700' },
  overseas_small: { text: '海外がわずかに高い（日本が現実的）', tone: 'bg-sky-50 text-sky-700' },
  overseas_clear: { text: '海外がはっきり高い', tone: 'bg-amber-50 text-amber-700' },
  japan_only: { text: '海外の比較なし', tone: 'bg-slate-100 text-slate-600' },
}

export function yen(value: number | null | undefined, signed = false): string {
  if (value === null || value === undefined) return '-'
  const sign = signed ? (value > 0 ? '+' : value < 0 ? '-' : '±') : value < 0 ? '-' : ''
  return `${sign}¥${Math.abs(Math.round(value)).toLocaleString()}`
}

export function money(value: number | null | undefined, currency: string): string {
  if (value === null || value === undefined) return '-'
  return `${CURRENCY_SIGN[currency] ?? `${currency} `}${Math.round(value).toLocaleString()}`
}

export function capacityLabel(capacity: string): string {
  return /^\d+$/.test(capacity) ? `${capacity}GB` : capacity
}

function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? '' : ` (${value > 0 ? '+' : ''}${value.toFixed(1)}%)`
}

function DirectionIcon({ direction }: { direction?: string | null }) {
  if (direction === 'up') return <TrendingUp className="h-4 w-4 text-emerald-600" aria-label="上昇" />
  if (direction === 'down') return <TrendingDown className="h-4 w-4 text-rose-600" aria-label="下落" />
  if (direction === 'flat') return <Minus className="h-4 w-4 text-slate-400" aria-label="横ばい" />
  return null
}

function Bar({ value, max, highlight }: { value: number; max: number; highlight: boolean }) {
  const width = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0
  return (
    <div className="h-1.5 w-full rounded-full bg-slate-100">
      <div className={`h-1.5 rounded-full ${highlight ? 'bg-violet-500' : 'bg-slate-300'}`} style={{ width: `${width}%` }} />
    </div>
  )
}

function QuotesBlock({ quotes }: { quotes: Quotes }) {
  const ranking = quotes.ranking ?? []
  const max = ranking[0]?.price ?? 0
  return (
    <div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>{quotes.store_count ?? 0}店</span>
        {quotes.median_price !== undefined && <span>中央値 {yen(quotes.median_price)}</span>}
        {quotes.spread !== undefined && <span>価格差 {yen(quotes.spread)}</span>}
        {quotes.retail_price && <span>定価比 {yen(quotes.best_vs_retail, true)}{percent(quotes.best_vs_retail_percent)}</span>}
      </div>
      <ul className="mt-2 space-y-1.5">
        {ranking.map((entry, index) => (
          <li key={entry.store} className="grid grid-cols-[1.5rem_minmax(0,1fr)_6rem] items-center gap-2 text-sm">
            <span className="text-xs text-slate-400">{index + 1}</span>
            <div className="min-w-0">
              <p className="truncate">
                {entry.store}
                {quotes.sponsored_stores?.includes(entry.store) && <span className="ml-1 rounded bg-slate-100 px-1 text-[10px] text-slate-500">PR</span>}
              </p>
              <Bar value={entry.price} max={max} highlight={index === 0} />
            </div>
            <span className="text-right font-medium tabular-nums">{yen(entry.price)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function TrendBlock({ trend }: { trend: Trend }) {
  if (!trend.days_of_data) return <p className="text-xs text-slate-400">値動きのデータはまだありません</p>
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
      <span className="inline-flex items-center gap-1"><DirectionIcon direction={trend.direction} />{trend.days_of_data}日分</span>
      {trend.change_7d && <span>7日前比 {yen(trend.change_7d.change, true)}{percent(trend.change_7d.percent)}</span>}
      {trend.change_30d && <span>30日前比 {yen(trend.change_30d.change, true)}{percent(trend.change_30d.percent)}</span>}
      {trend.high_30d !== undefined && <span>30日高値 {yen(trend.high_30d)}</span>}
      {trend.low_30d !== undefined && <span>30日安値 {yen(trend.low_30d)}</span>}
      {trend.slope_per_week !== undefined && trend.slope_per_week !== null && <span>傾き {yen(trend.slope_per_week, true)}/週</span>}
    </div>
  )
}

function GlobalBlock({ comparison }: { comparison: GlobalComparison }) {
  const max = comparison.ranking[0]?.price_jpy ?? 0
  const advice = ADVICE_LABELS[comparison.advice]
  return (
    <div>
      <p className="flex items-center gap-1.5 text-xs font-semibold text-slate-500"><Globe2 className="h-3.5 w-3.5" />世界比較</p>
      <ul className="mt-2 space-y-1.5">
        {comparison.ranking.map((entry) => (
          <li key={entry.market} className="grid grid-cols-[4.5rem_minmax(0,1fr)_6rem] items-center gap-2 text-sm">
            <span className={entry.market === 'jp' ? 'font-semibold' : ''}>{MARKET_LABELS[entry.market] ?? entry.market}</span>
            <div className="min-w-0">
              <p className="truncate text-xs text-slate-500">
                {entry.currency !== 'JPY' && `${money(entry.price, entry.currency)} `}
                {entry.store ?? ''}
                {entry.behind_top > 0 && ` ／1位より ${yen(-entry.behind_top, true)}`}
              </p>
              <Bar value={entry.price_jpy} max={max} highlight={entry.rank === 1} />
            </div>
            <span className="text-right font-medium tabular-nums">{yen(entry.price_jpy)}</span>
          </li>
        ))}
      </ul>
      <p className={`mt-2 inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs ${advice.tone}`}>
        {advice.text}
        {comparison.overseas_gap !== null && comparison.overseas_gap > 0 && ` ${yen(comparison.overseas_gap, true)}${percent(comparison.overseas_gap_percent)}`}
        <DirectionIcon direction={comparison.japan_direction} />
      </p>
    </div>
  )
}

function OverseasBlock({ markets }: { markets: OverseasMarket[] }) {
  return (
    <ul className="space-y-1 text-xs text-slate-600">
      {markets.map((market) => (
        <li key={market.market}>
          <span className="font-medium">{MARKET_LABELS[market.market] ?? market.market}</span>{' '}
          {money(market.price, market.currency)}
          {market.price_jpy !== null && ` = ${yen(market.price_jpy)}`}
          {market.vs_japan !== undefined && ` 日本比 ${yen(market.vs_japan, true)}${percent(market.vs_japan_percent)}`}
          {market.buyers !== undefined && ` ／${market.buyers}社`}
          {market.stores && market.stores.length > 0 && (
            <span className="block pl-3 text-slate-500">
              {market.stores.map((store) => `${store.store} ${money(store.price, store.currency)}`).join('、')}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

function ColorsBlock({ colors }: { colors: Colors }) {
  const requested = colors.requested
  const max = colors.colors[0]?.best_price ?? 0
  return (
    <div>
      <p className="flex items-center gap-1.5 text-xs font-semibold text-slate-500"><Palette className="h-3.5 w-3.5" />カラー別</p>
      {requested && (
        <p className="mt-1 rounded-lg bg-violet-50 px-2 py-1 text-xs text-violet-700">
          {requested.names.ja ?? requested.code}：
          {requested.quoted
            ? `${yen(requested.best_price)}（${requested.best_store}${requested.source === 'all_colors' ? '・全色同額' : ''}）${requested.behind_top ? ` 最高色より ${yen(-requested.behind_top, true)}` : ''}`
            : 'この色の価格なし'}
        </p>
      )}
      <ul className="mt-2 space-y-1.5">
        {colors.colors.map((color) => (
          <li key={color.code} className="grid grid-cols-[minmax(0,7rem)_minmax(0,1fr)_6rem] items-center gap-2 text-sm">
            <span className={`truncate ${requested?.code === color.code ? 'font-semibold text-violet-700' : ''}`}>{color.names.ja ?? color.code}</span>
            <div className="min-w-0">
              <p className="truncate text-xs text-slate-500">{color.best_store}／{color.store_count}店</p>
              <Bar value={color.best_price} max={max} highlight={color.rank === 1} />
            </div>
            <span className="text-right font-medium tabular-nums">{yen(color.best_price)}</span>
          </li>
        ))}
      </ul>
      {colors.all_colors && (
        <p className="mt-1 text-xs text-slate-500">全色同額の店：{colors.all_colors.best_store} {yen(colors.all_colors.best_price)}（{colors.all_colors.store_count}店）</p>
      )}
    </div>
  )
}

function CapacityCard({ model, entry }: { model: string; entry: CapacityEvidence }) {
  const [open, setOpen] = useState(true)
  const quotes = entry.quotes ?? {}
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-3">
      <button type="button" onClick={() => setOpen(!open)} className="flex w-full items-center justify-between text-left">
        <span className="font-semibold">{model} {capacityLabel(entry.capacity)}</span>
        <span className="flex items-center gap-2 text-sm">
          {quotes.best_price ? <span className="font-semibold tabular-nums">{yen(quotes.best_price)}</span> : <span className="text-slate-400">価格なし</span>}
          {open ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
        </span>
      </button>
      {open && (
        <div className="mt-3 space-y-4">
          {quotes.best_price ? <QuotesBlock quotes={quotes} /> : null}
          {entry.trend && <TrendBlock trend={entry.trend} />}
          {entry.global ? <GlobalBlock comparison={entry.global} /> : entry.overseas && entry.overseas.length > 0 && <OverseasBlock markets={entry.overseas} />}
          {entry.colors && entry.colors.colors.length > 0 && <ColorsBlock colors={entry.colors} />}
        </div>
      )}
    </article>
  )
}

function BulkCard({ bulk }: { bulk: Bulk }) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-3">
      <p className="font-semibold">まとめ売り 合計 {yen(bulk.total)}（{bulk.phones}台）</p>
      <ul className="mt-2 space-y-1 text-sm">
        {(bulk.lines ?? []).map((line, index) => (
          <li key={`${line.model}-${index}`} className="flex justify-between gap-2">
            <span className="truncate">{line.model} {capacityLabel(line.capacity)} ×{line.quantity}（{line.store}）</span>
            <span className="tabular-nums">{yen(line.subtotal)}</span>
          </li>
        ))}
      </ul>
      {bulk.single_store && (
        <p className="mt-2 text-xs text-slate-500">1店でまとめるなら {bulk.single_store.store} {yen(bulk.single_store.total)}</p>
      )}
    </article>
  )
}

function StoreCompareCard({ line }: { line: StoreCompareLine }) {
  const max = line.best_price ?? line.stores[0]?.price ?? 0
  return (
    <article className="rounded-xl border border-violet-200 bg-violet-50/40 p-3">
      <p className="font-semibold">店舗比較：{line.model} {capacityLabel(line.capacity)}</p>
      <ul className="mt-2 space-y-1.5">
        {line.stores.map((store) => (
          <li key={store.store} className="grid grid-cols-[minmax(0,8rem)_minmax(0,1fr)_6rem] items-center gap-2 text-sm">
            <span className={`truncate ${line.winner === store.store ? 'font-semibold text-violet-700' : ''}`}>{store.store}</span>
            <div className="min-w-0">
              <p className="truncate text-xs text-slate-500">{store.rank}位／{line.store_count}店{store.behind_best > 0 && ` ・最高値より ${yen(-store.behind_best, true)}`}</p>
              <Bar value={store.price} max={max} highlight={line.winner === store.store} />
            </div>
            <span className="text-right font-medium tabular-nums">{yen(store.price)}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-slate-600">
        {line.tie ? '同額です' : line.winner ? `${line.winner} が ${yen(line.gap)} 高い` : '比較できる店が 1 店だけです'}
        {!line.best_is_asked && line.best_store && ` ／最高値は ${line.best_store} ${yen(line.best_price)}`}
      </p>
      {line.unquoted.length > 0 && <p className="mt-1 text-xs text-amber-700">価格なし：{line.unquoted.join('、')}</p>}
    </article>
  )
}

function TargetCard({ line }: { line: TargetLine }) {
  return (
    <article className={`rounded-xl border p-3 ${line.reached ? 'border-emerald-200 bg-emerald-50/40' : 'border-rose-200 bg-rose-50/40'}`}>
      <p className="flex items-center gap-1.5 font-semibold">
        目標 {yen(line.target)}：{line.model} {capacityLabel(line.capacity)}
        <DirectionIcon direction={line.direction} />
      </p>
      <p className="mt-1 text-sm">
        {line.reached
          ? `${line.store_count}店中 ${line.reached_count}店が達成（最高 ${yen(line.best_price)}、目標より ${yen(line.best_vs_target, true)}）`
          : `未達：最高 ${yen(line.best_price)}（${line.best_store ?? '-'}）で ${yen(line.shortfall)} 足りません`}
      </p>
      {line.stores.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm">
          {line.stores.map((store) => (
            <li key={store.store} className="flex justify-between gap-2">
              <span className="truncate">{store.store}</span>
              <span className="tabular-nums">{yen(store.price)} <span className="text-xs text-emerald-700">{yen(store.over_target, true)}</span></span>
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}

export default function EvidenceCards({ evidence }: { evidence: PriceEvidence }) {
  const items = evidence.items ?? []
  if (items.length === 0 && !evidence.bulk) return null
  return (
    <div className="space-y-3">
      {(evidence.target_price?.items ?? []).map((line) => <TargetCard key={`target-${line.model}-${line.capacity}`} line={line} />)}
      {(evidence.store_compare?.items ?? []).map((line) => <StoreCompareCard key={`stores-${line.model}-${line.capacity}`} line={line} />)}
      {items.map((item, index) => (
        <div key={`${item.model}-${index}`} className="space-y-2">
          {(item.notes ?? []).length > 0 && (
            <p className="flex flex-wrap gap-1.5 text-xs">
              <span className="font-medium">{item.model}</span>
              {(item.notes ?? []).map((note) => (
                <span key={note} className="rounded bg-amber-50 px-1.5 py-0.5 text-amber-700">{NOTE_LABELS[note] ?? note}</span>
              ))}
            </p>
          )}
          {(item.capacities ?? []).map((entry) => <CapacityCard key={entry.capacity} model={item.model} entry={entry} />)}
        </div>
      ))}
      {evidence.bulk && <BulkCard bulk={evidence.bulk} />}
    </div>
  )
}
