import { useI18n } from '../i18n'
import { convert, type Currency } from './currency'
import type { ModelBoards } from './data'
import { MARKETS, bestPrice, capacityLabel, sortCapacities, type MarketBoard, type MarketId } from './markets'
import { globalText } from './text'
import { ColorDot, Diff, Money, PhoneArt, SampleBadge } from './ui'

const MARKET_IDS: MarketId[] = ['jp', 'hk', 'us']
type Rates = Partial<Record<Currency, number>>

/** Colour columns × capacity rows, like a shop price board. */
export function MarketTable({ board, currency, rates }: { board: MarketBoard; currency: Currency; rates: Rates }) {
  const { language } = useI18n()
  const text = globalText(language)
  const capacities = sortCapacities(Object.keys(board.prices))
  return (
    <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#121317]" data-testid="price-board">
      <table className="w-full min-w-[560px] border-collapse">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 w-28 bg-[#121317] sm:w-36" />
            {board.colors.map((color) => (
              <th key={color.code} className="px-3 pb-3 pt-5 text-left align-bottom font-normal">
                <PhoneArt model={board.model} color={color.code} />
                <p className="mt-2 text-sm text-slate-300">{color.name[language]}</p>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {capacities.map((capacity) => {
            const official = board.official[capacity]
            const top = bestPrice(board, capacity)
            const rowPrices = Object.values(board.prices[capacity] ?? {})
            const varies = new Set(rowPrices).size > 1 // mark "best" only when colours differ
            return (
              <tr key={capacity} className="border-t border-white/10">
                <td className="sticky left-0 z-10 bg-[#121317] px-3 py-4 align-top sm:px-4">
                  <p className="text-lg font-medium">{capacityLabel(capacity)}</p>
                  {official ? (
                    <>
                      <p className="mt-0.5 text-xs text-slate-500">{text.officialPrice}</p>
                      <Money amount={official} from={board.currency} to={currency} rates={rates} size="sm" />
                    </>
                  ) : null}
                </td>
                {board.colors.map((color) => {
                  const amount = board.prices[capacity]?.[color.code]
                  const stores = board.storeCount?.[capacity]?.[color.code]
                  return (
                    <td key={color.code} className="px-3 py-4 align-top">
                      {amount == null ? <span className="text-sm text-slate-600">—</span> : (
                        <div className="flex flex-col gap-0.5">
                          <span className="flex items-center gap-1.5 text-xs text-slate-500">
                            <ColorDot color={color.code} />
                            {capacityLabel(capacity)}
                            {varies && amount === top && <span className="font-semibold text-emerald-300">{text.best}</span>}
                          </span>
                          <Money amount={amount} from={board.currency} to={currency} rates={rates} emphasis={varies && amount === top} />
                          <Diff amount={amount} official={official} from={board.currency} to={currency} rates={rates} />
                          {stores ? <span className="text-[11px] text-slate-500">{text.stores(stores)}</span> : null}
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
export function GlobalBoard({ entry, currency, rates }: { entry: ModelBoards; currency: Currency; rates: Rates }) {
  const { language } = useI18n()
  const text = globalText(language)
  const capacities = sortCapacities([...new Set(MARKET_IDS.flatMap((id) => (entry[id] ? Object.keys(entry[id]!.prices) : [])))])
  return (
    <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[#121317]" data-testid="global-board">
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
