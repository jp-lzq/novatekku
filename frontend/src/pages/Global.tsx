import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { GlobalBoard, MarketTable } from '../global/boards'
import { useDisplayCurrency, useFxRates, type Currency } from '../global/currency'
import { useGlobalBoards, type ModelBoards } from '../global/data'
import { MARKETS, basePrice, capacityLabel, modelSlug, parseTab, tabCurrency, type MarketId, type Tab } from '../global/markets'
import { globalText } from '../global/text'
import { GlobalShell, Money, PhoneArt, SampleBadge } from '../global/ui'

const MARKET_IDS: MarketId[] = ['jp', 'hk', 'us']

function href(tab: Tab, model?: string) {
  const params = new URLSearchParams()
  if (tab !== 'global') params.set('m', tab)
  if (model) params.set('model', modelSlug(model))
  const query = params.toString()
  return `/global${query ? `?${query}` : ''}`
}

export default function Global() {
  const [params, setParams] = useSearchParams()
  const tab = parseTab(params.get('m'))
  const { language } = useI18n()
  const text = globalText(language)
  const { currency, manual, choose } = useDisplayCurrency(tabCurrency(tab))
  const { rates, updatedAt } = useFxRates()
  const { models, isLoading, isError } = useGlobalBoards()

  const visible = tab === 'global'
    ? models.filter((entry) => MARKET_IDS.filter((id) => entry[id]).length >= 2)
    : models.filter((entry) => entry[tab])
  const selected = visible.find((entry) => modelSlug(entry.model) === params.get('model')) ?? visible[0]

  const select = (entry: ModelBoards) => {
    const next = new URLSearchParams(params)
    next.set('model', modelSlug(entry.model))
    setParams(next, { replace: true })
  }

  return (
    <GlobalShell tab={tab} tabHref={(value) => href(value, selected?.model)} currency={currency} manualCurrency={manual} onCurrency={choose}>
      <section className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{text.title}</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">{text.subtitle}</p>
        </div>
        <p className="text-xs text-slate-500">{text.models(visible.length)}{updatedAt ? ` · ${text.rateNote(updatedAt.replace('T', ' ').slice(0, 16))}` : ''}</p>
      </section>

      {tab !== 'jp' && <p className="mt-4 rounded-xl border border-amber-400/25 bg-amber-400/5 px-4 py-2.5 text-xs text-amber-200/90">{text.sampleNote}</p>}
      {isLoading && <p className="mt-8 text-sm text-slate-500">{text.loading}</p>}
      {isError && <p className="mt-8 text-sm text-rose-400">{text.noData}</p>}

      {selected && (
        <div className="mt-6 grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
          {/* Model list: a column on desktop, a horizontal strip on phones */}
          <nav aria-label="models" data-testid="model-list" className="flex gap-2 overflow-x-auto pb-1 lg:max-h-[calc(100dvh-180px)] lg:flex-col lg:overflow-y-auto lg:overflow-x-visible lg:pb-0 lg:pr-1">
            {visible.map((entry) => (
              <ModelItem key={entry.model} entry={entry} tab={tab} active={entry === selected} currency={currency} rates={rates} onSelect={() => select(entry)} />
            ))}
          </nav>

          <section className="min-w-0" data-testid="model-detail">
            <div className="mb-3 flex flex-wrap items-center gap-3">
              <h2 className="text-xl font-semibold">{selected.model}</h2>
              {tab !== 'global' && selected[tab] && <SampleBadge sample={selected[tab]!.sample} />}
            </div>
            {tab === 'global'
              ? <GlobalBoard entry={selected} currency={currency} rates={rates} />
              : <MarketTable board={selected[tab]!} currency={currency} rates={rates} />}
          </section>
        </div>
      )}
    </GlobalShell>
  )
}

function ModelItem({ entry, tab, active, currency, rates, onSelect }: {
  entry: ModelBoards
  tab: Tab
  active: boolean
  currency: Currency
  rates: Partial<Record<Currency, number>>
  onSelect: () => void
}) {
  const ref = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    // keep the selected model visible in the horizontal strip on phones
    if (active) ref.current?.scrollIntoView({ block: 'nearest', inline: 'center' })
  }, [active])
  const board = tab === 'global' ? (entry.jp ?? entry.hk ?? entry.us)! : entry[tab]!
  const base = basePrice(board)
  const firstColor = board.colors[0]?.code ?? 'silver'
  return (
    <button
      ref={ref}
      type="button"
      onClick={onSelect}
      aria-current={active ? 'true' : undefined}
      className={`flex shrink-0 items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors lg:w-full ${
        active ? 'border-emerald-400/60 bg-emerald-400/10' : 'border-white/10 bg-white/[0.03] hover:border-white/25'
      }`}
    >
      <PhoneArt model={entry.model} color={firstColor} width={22} />
      <span className="min-w-0">
        <span className="block whitespace-nowrap text-sm font-medium">{entry.model}</span>
        {base && base.price != null && (
          <span className="flex items-baseline gap-1 whitespace-nowrap text-xs text-slate-500">
            {capacityLabel(base.capacity)}
            {tab === 'global'
              ? <span>{MARKET_IDS.filter((id) => entry[id]).map((id) => MARKETS[id].flag).join(' ')}</span>
              : <Money amount={base.price} from={board.currency} to={currency} rates={rates} size="sm" compact />}
          </span>
        )}
      </span>
    </button>
  )
}
