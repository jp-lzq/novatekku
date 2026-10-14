import { useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { GlobalBoard, MarketTable } from '../global/boards'
import { useDisplayCurrency, useFxRates, type Currency } from '../global/currency'
import { useGlobalBoards, type ModelBoards } from '../global/data'
import { MARKETS, basePrice, capacityLabel, generationOf, modelSlug, parseTab, tabCurrency, type MarketId, type Tab } from '../global/markets'
import { globalText } from '../global/text'
import { GlobalShell, Money, PhoneArt } from '../global/ui'

const MARKET_IDS: MarketId[] = ['jp', 'hk', 'us']

interface Generation {
  number: number
  models: ModelBoards[]
}

function href(tab: Tab, generation?: number) {
  const params = new URLSearchParams()
  if (tab !== 'global') params.set('m', tab)
  if (generation) params.set('gen', String(generation))
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
  const { models, updated, isLoading, isError } = useGlobalBoards()

  const visible = tab === 'global'
    ? models.filter((entry) => MARKET_IDS.filter((id) => entry[id]).length >= 2)
    : models.filter((entry) => entry[tab])
  const generations: Generation[] = []
  for (const entry of visible) {
    const number = generationOf(entry.model)
    const group = generations.find((item) => item.number === number)
    if (group) group.models.push(entry)
    else generations.push({ number, models: [entry] })
  }

  // ?model=<slug> (older links) selects that model's generation and scrolls to it
  const linkedModel = params.get('model')
  const linkedGeneration = visible.find((entry) => modelSlug(entry.model) === linkedModel)
  const wanted = Number(params.get('gen')) || (linkedGeneration ? generationOf(linkedGeneration.model) : 0)
  const selected = generations.find((item) => item.number === wanted) ?? generations[0]

  useEffect(() => {
    if (linkedModel) document.getElementById(`model-${linkedModel}`)?.scrollIntoView({ block: 'start' })
  }, [linkedModel, selected?.number])

  const select = (generation: Generation) => {
    const next = new URLSearchParams(params)
    next.set('gen', String(generation.number))
    next.delete('model')
    setParams(next) // new history entry, so Back returns to the previous generation
  }

  const marketUpdated = tab === 'hk' || tab === 'us' ? updated[tab] : null

  return (
    <GlobalShell tab={tab} tabHref={(value) => href(value, selected?.number)} currency={currency} manualCurrency={manual} onCurrency={choose}>
      <section className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{text.title}</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">{text.subtitle}</p>
        </div>
        <p className="text-xs text-slate-500">
          {text.models(visible.length)}
          {marketUpdated ? ` · ${text.priceUpdated(marketUpdated.replace('T', ' ').slice(0, 16))}` : ''}
          {updatedAt ? ` · ${text.rateNote(updatedAt.replace('T', ' ').slice(0, 16))}` : ''}
        </p>
      </section>

      {(tab === 'hk' || tab === 'us') && <p className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-xs text-slate-400">{text.marketNote[tab]}</p>}
      {isLoading && <p className="mt-8 text-sm text-slate-500">{text.loading}</p>}
      {isError && <p className="mt-8 text-sm text-rose-400">{text.noData}</p>}
      {!isLoading && !isError && generations.length === 0 && <p className="mt-8 text-sm text-slate-500">{text.noData}</p>}

      {selected && (
        <div className="mt-6 grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
          {/* Generation list: a column on desktop, a horizontal strip on phones */}
          <nav aria-label="generations" data-testid="generation-list" className="flex gap-2 overflow-x-auto pb-1 lg:sticky lg:top-28 lg:flex-col lg:self-start lg:overflow-visible lg:pb-0">
            {generations.map((generation) => (
              <GenerationItem key={generation.number} generation={generation} tab={tab} active={generation === selected} currency={currency} rates={rates} onSelect={() => select(generation)} />
            ))}
          </nav>

          <div className="min-w-0 space-y-8" data-testid="generation-detail">
            {selected.models.map((entry) => (
              <section key={entry.model} id={`model-${modelSlug(entry.model)}`} data-testid="model-detail" className="scroll-mt-28">
                <h2 className="mb-3 text-xl font-semibold">{entry.model}</h2>
                {tab === 'global'
                  ? <GlobalBoard entry={entry} currency={currency} rates={rates} />
                  : <MarketTable board={entry[tab]!} currency={currency} rates={rates} />}
              </section>
            ))}
          </div>
        </div>
      )}
    </GlobalShell>
  )
}

function GenerationItem({ generation, tab, active, currency, rates, onSelect }: {
  generation: Generation
  tab: Tab
  active: boolean
  currency: Currency
  rates: Partial<Record<Currency, number>>
  onSelect: () => void
}) {
  const { language } = useI18n()
  const text = globalText(language)
  const ref = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    // keep the selected generation visible in the horizontal strip on phones
    if (active) ref.current?.scrollIntoView({ block: 'nearest', inline: 'center' })
  }, [active])
  const lead = generation.models[0]
  const board = tab === 'global' ? (lead.jp ?? lead.hk ?? lead.us)! : lead[tab]!
  const base = basePrice(board)
  return (
    <button
      ref={ref}
      type="button"
      onClick={onSelect}
      aria-current={active ? 'true' : undefined}
      data-testid={`gen-${generation.number}`}
      className={`flex shrink-0 items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors lg:w-full ${
        active ? 'border-emerald-400/60 bg-emerald-400/10' : 'border-white/10 bg-white/[0.03] hover:border-white/25'
      }`}
    >
      <PhoneArt model={lead.model} color={board.colors[0]?.code ?? 'silver'} width={22} />
      <span className="min-w-0">
        <span className="block whitespace-nowrap text-sm font-semibold">iPhone {generation.number}</span>
        <span className="block whitespace-nowrap text-xs text-slate-500">{text.models(generation.models.length)}</span>
        {base?.price != null && tab !== 'global' && (
          <span className="block whitespace-nowrap text-xs text-slate-400">
            {capacityLabel(base.capacity)} {text.upTo} <Money amount={base.price} from={board.currency} to={currency} rates={rates} size="sm" compact />
          </span>
        )}
        {tab === 'global' && <span className="block text-xs">{MARKET_IDS.filter((id) => generation.models.some((entry) => entry[id])).map((id) => MARKETS[id].flag).join(' ')}</span>}
      </span>
    </button>
  )
}
