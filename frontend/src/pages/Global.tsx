import { ChevronRight } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { convert, useDisplayCurrency, useFxRates, type Currency } from '../global/currency'
import { useGlobalBoards, type ModelBoards } from '../global/data'
import { ALL_COLORS, MARKETS, bestPrice, capacityLabel, modelSlug, parseTab, sortCapacities, tabCurrency, type MarketBoard, type MarketId } from '../global/markets'
import { globalText } from '../global/text'
import { GlobalShell, Money, PhoneArt, SampleBadge } from '../global/ui'

const MARKET_IDS: MarketId[] = ['jp', 'hk', 'us']

function baseCapacity(board: MarketBoard) {
  return sortCapacities(Object.keys(board.prices))[0]
}

export default function Global() {
  const [params] = useSearchParams()
  const tab = parseTab(params.get('m'))
  const { language } = useI18n()
  const text = globalText(language)
  const { currency, manual, choose } = useDisplayCurrency(tabCurrency(tab))
  const { rates, updatedAt } = useFxRates()
  const { models, isLoading, isError } = useGlobalBoards()

  const visible = tab === 'global'
    ? models.filter((entry) => MARKET_IDS.filter((id) => entry[id]).length >= 2)
    : models.filter((entry) => entry[tab])

  return (
    <GlobalShell tab={tab} tabHref={(value) => (value === 'global' ? '/global' : `/global?m=${value}`)} currency={currency} manualCurrency={manual} onCurrency={choose}>
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

      <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" data-testid="model-list">
        {visible.map((entry) =>
          tab === 'global'
            ? <GlobalCard key={entry.model} entry={entry} currency={currency} rates={rates} />
            : <MarketCard key={entry.model} board={entry[tab]!} tab={tab} currency={currency} rates={rates} />,
        )}
      </section>
    </GlobalShell>
  )
}

function MarketCard({ board, tab, currency, rates }: { board: MarketBoard; tab: MarketId; currency: Currency; rates: Partial<Record<Currency, number>> }) {
  const { language } = useI18n()
  const text = globalText(language)
  const capacity = baseCapacity(board)
  const color = board.colors[0] === ALL_COLORS ? 'silver' : board.colors[0]
  return (
    <Link to={`/global/${modelSlug(board.model)}?m=${tab}`} className="group flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-emerald-400/40 hover:bg-white/[0.05]">
      <PhoneArt color={color} className="h-16 w-9 shrink-0" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium">{board.model}</p>
          <SampleBadge sample={board.sample} />
        </div>
        <p className="mt-1 text-xs text-slate-500">{capacityLabel(capacity)} {text.best}{board.storeCount?.[capacity] ? ` · ${text.stores(board.storeCount[capacity])}` : ''}</p>
        <div className="mt-1"><Money amount={bestPrice(board, capacity)} from={board.currency} to={currency} rates={rates} /></div>
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-slate-600 group-hover:text-emerald-300" />
    </Link>
  )
}

function GlobalCard({ entry, currency, rates }: { entry: ModelBoards; currency: Currency; rates: Partial<Record<Currency, number>> }) {
  const { language } = useI18n()
  const text = globalText(language)
  const capacities = sortCapacities([...new Set(MARKET_IDS.flatMap((id) => (entry[id] ? Object.keys(entry[id]!.prices) : [])))])
  const capacity = capacities.find((value) => MARKET_IDS.filter((id) => entry[id]?.prices[value]).length >= 2) ?? capacities[0]
  const rows = MARKET_IDS.map((id) => {
    const board = entry[id]
    const amount = board ? bestPrice(board, capacity) : null
    return { id, board, amount, yen: board && amount != null ? convert(amount, board.currency, 'JPY', rates) : null }
  })
  const top = Math.max(...rows.map((row) => row.yen ?? -1))

  return (
    <Link to={`/global/${modelSlug(entry.model)}`} className="group rounded-2xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-emerald-400/40 hover:bg-white/[0.05]">
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium">{entry.model}</p>
        <span className="text-xs text-slate-500">{capacityLabel(capacity)}</span>
      </div>
      <ul className="mt-3 space-y-2">
        {rows.map((row) => (
          <li key={row.id} className={`flex items-center justify-between rounded-xl px-3 py-2 ${row.yen != null && row.yen === top ? 'bg-emerald-400/10 ring-1 ring-emerald-400/30' : 'bg-white/[0.02]'}`}>
            <span className="flex items-center gap-2 text-sm text-slate-300">
              <span aria-hidden>{MARKETS[row.id].flag}</span>{text.tabs[row.id]}
              {row.yen != null && row.yen === top && <span className="text-[11px] font-semibold text-emerald-300">{text.highest}</span>}
            </span>
            {row.board ? <Money amount={row.amount} from={row.board.currency} to={currency} rates={rates} size="sm" emphasis={row.yen === top} /> : <span className="text-xs text-slate-600">{text.noData}</span>}
          </li>
        ))}
      </ul>
    </Link>
  )
}
