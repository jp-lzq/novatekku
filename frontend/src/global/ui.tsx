import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useI18n, type Language } from '../i18n'
import { CURRENCIES, convert, formatMoney, type Currency } from './currency'
import { COLOR_HEX, MARKETS, isLarge, phoneShape, type Tab } from './markets'
import { globalText } from './text'

const TABS: Tab[] = ['global', 'jp', 'hk', 'us']
const LANGUAGES: Language[] = ['zh', 'ja', 'en']
const LANGUAGE_LABEL: Record<Language, string> = { zh: '中文', ja: '日本語', en: 'English' }

/** Keep the global section out of search results until live data exists. */
export function useNoIndex() {
  useEffect(() => {
    const tag = document.createElement('meta')
    tag.name = 'robots'
    tag.content = 'noindex, nofollow'
    document.head.appendChild(tag)
    return () => tag.remove()
  }, [])
}

export function GlobalShell({
  tab,
  tabHref,
  currency,
  manualCurrency,
  onCurrency,
  children,
}: {
  tab: Tab
  tabHref: (tab: Tab) => string
  currency: Currency
  manualCurrency: Currency | null
  onCurrency: (value: Currency | 'auto') => void
  children: ReactNode
}) {
  const { language, setLanguage } = useI18n()
  const text = globalText(language)
  useNoIndex()

  return (
    <div className="min-h-[100dvh] bg-[#0b0c0f] text-slate-100">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-[#0b0c0f]/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
          <Link to="/global" className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-emerald-400 to-sky-500 text-sm font-bold text-black">N</span>
            <span className="text-sm font-semibold tracking-wide">{text.brand}</span>
          </Link>
          <div className="ml-auto flex items-center gap-2">
            <label className="sr-only" htmlFor="global-language">{text.language}</label>
            <select
              id="global-language"
              value={language}
              onChange={(event) => setLanguage(event.target.value as Language)}
              className="h-9 rounded-lg border border-white/15 bg-white/5 px-2 text-xs text-slate-200 outline-none focus:border-emerald-400/60"
            >
              {LANGUAGES.map((value) => <option key={value} value={value} className="bg-[#16181d]">{LANGUAGE_LABEL[value]}</option>)}
            </select>
            <label className="sr-only" htmlFor="global-currency">{text.currency}</label>
            <select
              id="global-currency"
              data-testid="currency-select"
              value={manualCurrency ?? 'auto'}
              onChange={(event) => onCurrency(event.target.value as Currency | 'auto')}
              className="h-9 rounded-lg border border-emerald-400/40 bg-emerald-400/10 px-2 text-xs font-semibold text-emerald-200 outline-none focus:border-emerald-300"
            >
              <option value="auto" className="bg-[#16181d]">{text.auto} · {currency}</option>
              {CURRENCIES.map((value) => <option key={value} value={value} className="bg-[#16181d]">{value}</option>)}
            </select>
          </div>
        </div>
        <nav className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 sm:px-6" aria-label="markets">
          {TABS.map((value) => (
            <Link
              key={value}
              to={tabHref(value)}
              data-testid={`tab-${value}`}
              className={`flex shrink-0 items-center gap-1 border-b-2 px-2 py-2.5 text-[13px] transition-colors sm:gap-1.5 sm:px-3 sm:text-sm ${
                tab === value ? 'border-emerald-400 font-semibold text-white' : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <span aria-hidden>{value === 'global' ? '🌐' : MARKETS[value].flag}</span>
              {text.tabs[value]}
            </Link>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 pb-16 pt-6 sm:px-6">{children}</main>
    </div>
  )
}

/** Converted price, with the original amount underneath when the currency differs. */
export function Money({
  amount,
  from,
  to,
  rates,
  size = 'md',
  emphasis = false,
  compact = false,
}: {
  amount: number | null | undefined
  from: Currency
  to: Currency
  rates: Partial<Record<Currency, number>>
  size?: 'sm' | 'md' | 'lg'
  emphasis?: boolean
  compact?: boolean // one line, no original amount (used in lists)
}) {
  const { language } = useI18n()
  const text = globalText(language)
  if (amount == null) return <span className="text-sm text-slate-500">—</span>
  const converted = convert(amount, from, to, rates)
  const sizeClass = size === 'lg' ? 'text-2xl' : size === 'sm' ? 'text-sm' : 'text-lg'
  if (compact) {
    return <span className="font-semibold tabular-nums text-slate-200">{converted == null ? formatMoney(amount, from) : formatMoney(converted, to)}</span>
  }
  return (
    <span className="inline-flex flex-col leading-tight">
      <span className={`${sizeClass} font-semibold tabular-nums ${emphasis ? 'text-emerald-300' : 'text-slate-50'}`}>
        {converted == null ? formatMoney(amount, from) : formatMoney(converted, to)}
      </span>
      {from !== to && converted != null && (
        <span className="text-[11px] tabular-nums text-slate-500">({text.original} {formatMoney(amount, from)})</span>
      )}
    </span>
  )
}

/** Difference against the official price, red below and green above. */
export function Diff({ amount, official, from, to, rates }: {
  amount: number
  official: number | null | undefined
  from: Currency
  to: Currency
  rates: Partial<Record<Currency, number>>
}) {
  if (!official) return null
  const converted = convert(amount - official, from, to, rates)
  const difference = converted ?? amount - official
  const shown = converted == null ? from : to
  const tone = difference > 0 ? 'text-emerald-400' : difference < 0 ? 'text-rose-400' : 'text-slate-400'
  return <span className={`text-xs tabular-nums ${tone}`}>({formatMoney(difference, shown, true)})</span>
}

export function ColorDot({ color, size = 12 }: { color: string; size?: number }) {
  return <span className="inline-block shrink-0 rounded-full ring-1 ring-white/30" style={{ width: size, height: size, background: COLOR_HEX[color] ?? '#8b93a1' }} />
}

function shade(hex: string, amount: number) {
  const value = parseInt(hex.slice(1), 16)
  const channel = (shift: number) => Math.max(0, Math.min(255, ((value >> shift) & 255) + amount))
  return `rgb(${channel(16)},${channel(8)},${channel(0)})`
}

function Lens({ x, y, r, body }: { x: number; y: number; r: number; body: string }) {
  return (
    <g>
      <circle cx={x} cy={y} r={r} fill={shade(body, -40)} stroke={shade(body, 30)} strokeWidth={0.8} />
      <circle cx={x} cy={y} r={r * 0.62} fill="#0d0f14" />
      <circle cx={x - r * 0.22} cy={y - r * 0.22} r={r * 0.16} fill="#ffffff" opacity={0.35} />
    </g>
  )
}

/** Back of the phone drawn per model family (camera layout and body proportions) in the finish colour. */
export function PhoneArt({ model, color, width = 46 }: { model: string; color: string; width?: number }) {
  const body = COLOR_HEX[color] ?? '#8b93a1'
  const shape = phoneShape(model)
  const h = shape === 'fold' ? 88 : isLarge(model) ? 100 : 94
  const w = shape === 'fold' ? 76 : 50 // the foldable is drawn opened: two panels side by side
  const id = `g-${model.replace(/\W/g, '')}-${color}`
  const camera = (() => {
    switch (shape) {
      case 'fold':
        return (
          <g>
            <line x1={38} y1={2} x2={38} y2={h - 2} stroke={shade(body, -35)} strokeWidth={1.4} />
            <rect x={3} y={6} width={31} height={15} rx={7} fill={shade(body, -18)} />
            <Lens x={10} y={13.5} r={4} body={body} /><Lens x={20} y={13.5} r={4} body={body} />
            <circle cx={29} cy={13.5} r={1.4} fill="#f6e7b0" />
          </g>
        )
      case 'plateau':
        return (
          <g>
            <rect x={3} y={6} width={44} height={24} rx={8} fill={shade(body, -14)} />
            <rect x={5} y={8} width={23} height={20} rx={6} fill={shade(body, -26)} />
            <Lens x={11} y={13.5} r={4} body={body} /><Lens x={11} y={23} r={4} body={body} /><Lens x={21} y={18.3} r={4} body={body} />
            <circle cx={39} cy={13} r={1.6} fill="#f6e7b0" /><circle cx={39} cy={23} r={1.3} fill="#0d0f14" />
          </g>
        )
      case 'air':
        return (
          <g>
            <rect x={3} y={7} width={44} height={13} rx={6.5} fill={shade(body, -18)} />
            <Lens x={11} y={13.5} r={4} body={body} /><circle cx={21} cy={13.5} r={1.4} fill="#f6e7b0" />
          </g>
        )
      case 'pill':
        return (
          <g>
            <rect x={6} y={6} width={12} height={23} rx={6} fill={shade(body, -18)} />
            <Lens x={12} y={12} r={4} body={body} /><Lens x={12} y={23} r={4} body={body} />
            <circle cx={22} cy={12} r={1.4} fill="#f6e7b0" />
          </g>
        )
      case 'proTriple':
        return (
          <g>
            <rect x={5} y={5} width={23} height={23} rx={6} fill={shade(body, -18)} />
            <Lens x={11} y={11} r={4} body={body} /><Lens x={11} y={22} r={4} body={body} /><Lens x={21} y={16.5} r={4} body={body} />
            <circle cx={22} cy={8.5} r={1.3} fill="#f6e7b0" />
          </g>
        )
      case 'diagonal':
        return (
          <g>
            <rect x={5} y={5} width={21} height={21} rx={6} fill={shade(body, -18)} />
            <Lens x={11} y={11} r={4} body={body} /><Lens x={20} y={20} r={4} body={body} />
            <circle cx={21} cy={10} r={1.3} fill="#f6e7b0" />
          </g>
        )
      default:
        return (
          <g>
            <Lens x={11} y={11} r={4.4} body={body} /><circle cx={20} cy={11} r={1.3} fill="#f6e7b0" />
          </g>
        )
    }
  })()
  return (
    <svg width={(width * w) / 50} height={(width * h) / 50} viewBox={`0 0 ${w} ${h}`} role="img" aria-label={`${model} ${color}`}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={shade(body, 22)} />
          <stop offset="0.55" stopColor={body} />
          <stop offset="1" stopColor={shade(body, -30)} />
        </linearGradient>
      </defs>
      <rect x={0.75} y={0.75} width={w - 1.5} height={h - 1.5} rx={9} fill={`url(#${id})`} stroke={shade(body, 40)} strokeOpacity={0.5} strokeWidth={1.2} />
      {camera}
      <path d={`M${w / 2 - (shape === 'fold' ? -15 : 4)} ${h / 2 + 4} a4 4 0 1 0 8 0 a4 4 0 1 0 -8 0`} fill={shade(body, -10)} opacity={0.5} />
    </svg>
  )
}

export function SampleBadge({ sample }: { sample: boolean }) {
  const { language } = useI18n()
  const text = globalText(language)
  return sample ? (
    <span className="rounded-full border border-amber-400/40 bg-amber-400/10 px-2 py-0.5 text-[11px] font-medium text-amber-300">{text.sample}</span>
  ) : (
    <span className="rounded-full border border-emerald-400/40 bg-emerald-400/10 px-2 py-0.5 text-[11px] font-medium text-emerald-300">{text.live}</span>
  )
}
