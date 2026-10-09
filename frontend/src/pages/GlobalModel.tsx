import { ArrowLeft } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { convert, useDisplayCurrency, useFxRates, type Currency } from '../global/currency'
import { useGlobalBoards, type ModelBoards } from '../global/data'
import { ALL_COLORS, COLORS, MARKETS, bestPrice, capacityLabel, modelSlug, parseTab, sortCapacities, tabCurrency, type MarketBoard, type MarketId } from '../global/markets'
import { globalText } from '../global/text'
import { ColorDot, Diff, GlobalShell, Money, PhoneArt, SampleBadge } from '../global/ui'

const MARKET_IDS: MarketId[] = ['jp', 'hk', 'us']
type Rates = Partial<Record<Currency, number>>

export default function GlobalModel() {
  const { slug = '' } = useParams()
  const [params] = useSearchParams()
  const tab = parseTab(params.get('m'))
  const { language } = useI18n()
  const text = globalText(language)
  const { currency, manual, choose } = useDisplayCurrency(tabCurrency(tab))
  const { rates } = useFxRates()
  const { models, isLoading } = useGlobalBoards()
  const entry = models.find((item) => modelSlug(item.model) === slug)
  const board = tab === 'global' ? undefined : entry?.[tab]

  return (
    <GlobalShell tab={tab} tabHref={(value) => `/global/${slug}${value === 'global' ? '' : `?m=${value}`}`} currency={currency} manualCurrency={manual} onCurrency={choose}>
      <Link to={tab === 'global' ? '/global' : `/global?m=${tab}`} className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white">
        <ArrowLeft className="h-4 w-4" />{text.back}
      </Link>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">{entry?.model ?? slug}</h1>
        <span className="text-sm text-slate-500">{text.detail}</span>
        {board && <SampleBadge sample={board.sample} />}
      </div>

      {isLoading && <p className="mt-8 text-sm text-slate-500">{text.loading}</p>}
      {!isLoading && !entry && <p className="mt-8 text-sm text-slate-500">{text.noData}</p>}
      {entry && tab === 'global' && <GlobalBoard entry={entry} currency={currency} rates={rates} />}
      {entry && tab !== 'global' && (board ? <MarketTable board={board} currency={currency} rates={rates} /> : <p className="mt-8 text-sm text-slate-500">{text.noData}</p>)}
    </GlobalShell>
  )
}

/** Colour columns × capacity rows, like a shop price board. */
function MarketTable({ board, currency, rates }: { board: MarketBoard; currency: Currency; rates: Rates }) {
  const { language } = useI18n()
  const text = globalText(language)
  const capacities = sortCapacities(Object.keys(board.prices))
  return (
    <div className="mt-6 overflow-x-auto rounded-2xl border border-white/10 bg-[#121317]" data-testid="price-board">
      <table className="w-full min-w-[560px] border-collapse">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 w-28 bg-[#121317] sm:w-40" />
            {board.colors.map((color) => (
              <th key={color} className="px-3 pb-3 pt-5 text-left align-bottom font-normal">
                <PhoneArt color={color === ALL_COLORS ? 'silver' : color} />
                <p className="mt-2 text-sm text-slate-300">{color === ALL_COLORS ? text.allColors : COLORS[color]?.name[language] ?? color}</p>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {capacities.map((capacity) => {
            const official = board.official[capacity]
            const top = bestPrice(board, capacity)
            return (
              <tr key={capacity} className="border-t border-white/10">
                <td className="sticky left-0 z-10 bg-[#121317] px-3 py-4 align-top sm:px-4">
                  <p className="text-lg font-medium">{capacityLabel(capacity)}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{text.officialPrice}</p>
                  {official ? <Money amount={official} from={board.currency} to={currency} rates={rates} size="sm" /> : <span className="text-xs text-slate-600">—</span>}
                </td>
                {board.colors.map((color) => {
                  const amount = board.prices[capacity]?.[color]
                  return (
                    <td key={color} className="px-3 py-4 align-top">
                      {amount == null ? <span className="text-sm text-slate-600">—</span> : (
                        <div className="flex flex-col gap-0.5">
                          <span className="flex items-center gap-1.5 text-xs text-slate-500">
                            <ColorDot color={color} />
                            {capacityLabel(capacity)}
                            {board.colors.length > 1 && amount === top && <span className="font-semibold text-emerald-300">{text.best}</span>}
                          </span>
                          <Money amount={amount} from={board.currency} to={currency} rates={rates} emphasis={board.colors.length > 1 && amount === top} />
                          <Diff amount={amount} official={official} from={board.currency} to={currency} rates={rates} />
                          {board.storeCount?.[capacity] ? <span className="text-[11px] text-slate-500">{text.stores(board.storeCount[capacity])}</span> : null}
                        </div>
                      )}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

/** Capacity rows × market columns; the market paying the most is highlighted. */
function GlobalBoard({ entry, currency, rates }: { entry: ModelBoards; currency: Currency; rates: Rates }) {
  const { language } = useI18n()
  const text = globalText(language)
  const capacities = sortCapacities([...new Set(MARKET_IDS.flatMap((id) => (entry[id] ? Object.keys(entry[id]!.prices) : [])))])
  return (
    <div className="mt-6 overflow-x-auto rounded-2xl border border-white/10 bg-[#121317]" data-testid="global-board">
      <table className="w-full min-w-[560px] border-collapse">
        <thead>
          <tr className="text-left text-sm text-slate-400">
            <th className="sticky left-0 z-10 bg-[#121317] px-4 py-4 font-normal">{text.capacity}</th>
            {MARKET_IDS.map((id) => (
              <th key={id} className="px-3 py-4 font-normal">
                <span className="flex items-center gap-2"><span aria-hidden>{MARKETS[id].flag}</span>{text.tabs[id]}</span>
                {entry[id] && <span className="mt-1 inline-block"><SampleBadge sample={entry[id]!.sample} /></span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {capacities.map((capacity) => {
            const cells = MARKET_IDS.map((id) => {
              const board = entry[id]
              const amount = board ? bestPrice(board, capacity) : null
              return { id, board, amount, yen: board && amount != null ? convert(amount, board.currency, 'JPY', rates) : null }
            })
            const top = Math.max(...cells.map((cell) => cell.yen ?? -1))
            const japan = cells[0].yen
            return (
              <tr key={capacity} className="border-t border-white/10">
                <td className="sticky left-0 z-10 bg-[#121317] px-4 py-4 text-lg font-medium">{capacityLabel(capacity)}</td>
                {cells.map((cell) => (
                  <td key={cell.id} className={`px-3 py-4 align-top ${cell.yen != null && cell.yen === top ? 'bg-emerald-400/10' : ''}`}>
                    {cell.board && cell.amount != null ? (
                      <div className="flex flex-col gap-0.5">
                        <Money amount={cell.amount} from={cell.board.currency} to={currency} rates={rates} emphasis={cell.yen === top} />
                        {cell.yen === top && <span className="text-[11px] font-semibold text-emerald-300">{text.bestMarket}</span>}
                        {cell.id !== 'jp' && japan && cell.yen != null && (
                          <span className={`text-xs tabular-nums ${cell.yen >= japan ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {text.vsJapan} {cell.yen >= japan ? '+' : ''}{(((cell.yen - japan) / japan) * 100).toFixed(1)}%
                          </span>
                        )}
                      </div>
                    ) : <span className="text-sm text-slate-600">{text.noData}</span>}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
