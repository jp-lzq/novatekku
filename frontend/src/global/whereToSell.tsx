import { useState } from 'react'
import { useI18n } from '../i18n'
import { formatMoney } from './currency'
import { useWhereToSell, type WhereToSellMarket, type WhereToSellResponse } from './data'
import { MARKETS, capacityLabel, japanTime } from './markets'
import { globalText, type GlobalText } from './text'

type Tone = 'dark' | 'light'

// the global pages are dark, the product page is light; the card follows its page
const TONES: Record<Tone, { card: string; muted: string; strong: string; track: string; bar: string; best: string; bestBar: string; chip: string; chipActive: string }> = {
  dark: {
    card: 'rounded-2xl border border-white/10 bg-[#121317] p-4',
    muted: 'text-slate-500',
    strong: 'text-slate-200',
    track: 'bg-white/[0.06]',
    bar: 'bg-slate-500/60',
    best: 'text-emerald-300',
    bestBar: 'bg-emerald-400',
    chip: 'border-white/10 text-slate-400 hover:border-white/25',
    chipActive: 'border-emerald-400/60 bg-emerald-400/10 text-emerald-200',
  },
  light: {
    card: 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6',
    muted: 'text-slate-500',
    strong: 'text-slate-900',
    track: 'bg-slate-100',
    bar: 'bg-slate-300',
    best: 'text-emerald-700',
    bestBar: 'bg-emerald-500',
    chip: 'border-slate-200 text-slate-500 hover:border-slate-300',
    chipActive: 'border-emerald-300 bg-emerald-50 text-emerald-700',
  },
}

const yen = (amount: number) => formatMoney(amount, 'JPY')
const signedPercent = (value: number) => `${value > 0 ? '+' : ''}${value.toFixed(1)}`

/** The one-sentence recommendation, or null when there is nothing to recommend. */
export function adviceSentence(data: WhereToSellResponse, text: GlobalText): string | null {
  const copy = text.whereToSell
  if (data.markets.length === 0) return null
  if (!data.advice) return copy.noJapan
  if (data.advice === 'japan_only') return copy.advice.japan_only
  const gap = data.overseas_gap ?? 0
  if (data.advice === 'japan_best') return copy.advice.japan_best(yen(-gap))
  const market = data.best_overseas_market ? text.tabs[data.best_overseas_market] : ''
  const percent = (data.overseas_gap_percent ?? 0).toFixed(1)
  return copy.advice[data.advice](market, yen(gap), percent)
}

function directionSentence(data: WhereToSellResponse, text: GlobalText): string | null {
  if (!data.japan_direction || !data.japan_change_7d) return null
  return text.whereToSell.direction[data.japan_direction](signedPercent(data.japan_change_7d.percent))
}

/**
 * "Where does it sell best?": Japan, Hong Kong and the US as bars in yen, the best one highlighted,
 * with a one-line recommendation.  ``capacity`` fixes the capacity (product page); without it the
 * card offers the capacities that have prices (global page).
 */
export function WhereToSell({ model, capacity, tone = 'dark', className = 'mt-3' }: {
  model: string
  capacity?: string | null
  tone?: Tone
  className?: string
}) {
  const { language } = useI18n()
  const text = globalText(language)
  const style = TONES[tone]
  const [picked, setPicked] = useState<string | null>(null)
  const { data, isError } = useWhereToSell(model, capacity ?? picked)
  if (isError || !data) return null
  const fixed = Boolean(capacity)
  if (fixed && data.markets.length === 0) return null // a product page without prices shows no empty card

  const top = data.markets[0]?.price_jpy ?? 0
  const advice = adviceSentence(data, text)
  const direction = directionSentence(data, text)
  // newest price time among the markets shown (offsets differ, so compare as dates)
  const latest = data.markets
    .map((entry) => data.updated_at[entry.market])
    .filter((value): value is string => Boolean(value))
    .reduce<string | null>((newest, value) => (!newest || Date.parse(value) > Date.parse(newest) ? value : newest), null)

  return (
    <div className={`${className} ${style.card}`} data-testid="where-to-sell">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className={`text-sm font-semibold ${style.strong}`}>
          {text.whereToSell.title}
          {data.capacity && <span className={`ml-2 font-normal ${style.muted}`}>{capacityLabel(data.capacity)}</span>}
        </h3>
        <span className={`text-xs ${style.muted}`}>{text.whereToSell.inYen}</span>
      </div>

      {!fixed && data.capacities.length > 1 && (
        <div className="mt-3 flex flex-wrap gap-1.5" role="group" aria-label={text.capacity}>
          {data.capacities.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setPicked(value)}
              aria-pressed={value === data.capacity}
              className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${value === data.capacity ? style.chipActive : style.chip}`}
            >
              {capacityLabel(value)}
            </button>
          ))}
        </div>
      )}

      {data.markets.length === 0
        ? <p className={`mt-3 text-sm ${style.muted}`}>{text.whereToSell.noPrices}</p>
        : (
          <ol className="mt-3 space-y-2.5">
            {data.markets.map((entry) => <MarketBar key={entry.market} entry={entry} top={top} tone={tone} text={text} />)}
          </ol>
        )}

      {advice && <p className={`mt-3 text-sm leading-relaxed ${style.strong}`} data-testid="where-to-sell-advice">{advice}</p>}
      {direction && <p className={`mt-1 text-xs ${data.japan_direction === 'down' ? 'text-rose-500' : style.muted}`}>{direction}</p>}

      <p className={`mt-3 text-[11px] ${style.muted}`}>
        {latest ? text.whereToSell.prices(japanTime(latest)) : ''}
        {latest && data.fx.updated_at ? ' · ' : ''}
        {data.fx.updated_at ? text.whereToSell.rates(data.fx.updated_at.replace('T', ' ').slice(0, 16)) : ''}
      </p>
    </div>
  )
}

function MarketBar({ entry, top, tone, text }: { entry: WhereToSellMarket; top: number; tone: Tone; text: GlobalText }) {
  const style = TONES[tone]
  const best = entry.rank === 1
  const width = top > 0 ? Math.max(4, Math.round((entry.price_jpy / top) * 100)) : 0
  return (
    <li>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="flex min-w-0 items-baseline gap-2">
          <span aria-hidden>{MARKETS[entry.market].flag}</span>
          <span className={best ? `font-semibold ${style.best}` : style.strong}>{text.tabs[entry.market]}</span>
          {best && <span className={`text-[11px] font-semibold ${style.best}`}>{text.whereToSell.highest}</span>}
          {entry.store && <span className={`truncate text-xs ${style.muted}`}>{entry.store}</span>}
        </span>
        <span className="flex shrink-0 items-baseline gap-2">
          {entry.currency !== 'JPY' && <span className={`text-[11px] tabular-nums ${style.muted}`}>({formatMoney(entry.price, entry.currency)})</span>}
          <span className={`font-semibold tabular-nums ${best ? style.best : style.strong}`}>{yen(entry.price_jpy)}</span>
        </span>
      </div>
      <div className={`mt-1 h-2 overflow-hidden rounded-full ${style.track}`}>
        <div className={`h-full rounded-full ${best ? style.bestBar : style.bar}`} style={{ width: `${width}%` }} />
      </div>
      <p className={`mt-0.5 flex justify-between text-[11px] ${style.muted}`}>
        <span>{entry.buyers ? text.whereToSell.buyers(entry.buyers) : ''}</span>
        <span className="tabular-nums">{best ? '' : text.whereToSell.behind(yen(entry.behind_top))}</span>
      </p>
    </li>
  )
}
