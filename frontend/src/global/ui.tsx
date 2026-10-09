import { useEffect, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useI18n, type Language } from '../i18n'
import { CURRENCIES, convert, formatMoney, type Currency } from './currency'
import { COLORS, MARKETS, type Tab } from './markets'
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
              className={`flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm transition-colors ${
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
}: {
  amount: number | null | undefined
  from: Currency
  to: Currency
  rates: Partial<Record<Currency, number>>
  size?: 'sm' | 'md' | 'lg'
  emphasis?: boolean
}) {
  const { language } = useI18n()
  const text = globalText(language)
  if (amount == null) return <span className="text-sm text-slate-500">—</span>
  const converted = convert(amount, from, to, rates)
  const sizeClass = size === 'lg' ? 'text-2xl' : size === 'sm' ? 'text-sm' : 'text-lg'
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
  const hex = COLORS[color]?.hex
  if (!hex) return <span className="inline-block rounded-full bg-gradient-to-br from-slate-200 via-sky-300 to-rose-300" style={{ width: size, height: size }} />
  return <span className="inline-block rounded-full ring-1 ring-white/30" style={{ width: size, height: size, background: hex }} />
}

/** Simple phone silhouette tinted with the colour (no product photos needed). */
export function PhoneArt({ color, className = 'h-20 w-11' }: { color: string; className?: string }) {
  const hex = COLORS[color]?.hex ?? '#8b93a1'
  return (
    <span className={`relative inline-block rounded-[10px] ring-1 ring-white/20 ${className}`} style={{ background: `linear-gradient(150deg, ${hex}, ${hex}cc 60%, #00000055)` }}>
      <span className="absolute left-1 top-1 h-4 w-4 rounded-[5px] bg-black/35 ring-1 ring-white/15" />
      <span className="absolute left-[7px] top-[7px] h-1.5 w-1.5 rounded-full bg-black/60" />
    </span>
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
