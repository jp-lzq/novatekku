import { useState } from 'react'
import { useI18n } from '../i18n'
import { convert, type Currency } from './currency'
import type { MarketStoreResponse, ModelBoards } from './data'
import { ALL_COLORS, MARKETS, bestPrice, capacityLabel, japanTime, sortCapacities, type MarketBoard, type MarketId } from './markets'
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
              <th key={color.code} className={`px-3 pb-3 pt-5 text-left align-bottom font-normal ${color.code === ALL_COLORS ? 'border-l border-white/10' : ''}`}>
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
                    <td key={color.code} className={`px-3 py-4 align-top ${color.code === ALL_COLORS ? 'border-l border-white/10' : ''}`}>
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

const TOP_STORES = 5

/** Store-by-store prices for one model, like the Japanese price table: every capacity, best first. */
export function StoreRanking({ model, data, currency, rates }: {
  model: string
  data: MarketStoreResponse | undefined
  currency: Currency
  rates: Rates
}) {
  const { language } = useI18n()
  const text = globalText(language)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const rows = (data?.products ?? []).filter((row) => row.model === model && row.color_code === null && row.stores.length > 0)
  if (!data || rows.length === 0) return null
  return (
    <div className="mt-3 rounded-2xl border border-white/10 bg-[#121317] p-4" data-testid="store-ranking">
      <h3 className="text-sm font-semibold text-slate-300">{text.storeRanking}</h3>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {sortCapacities(rows.map((row) => row.capacity)).map((capacity) => {
          const row = rows.find((item) => item.capacity === capacity)!
          const open = expanded[capacity] ?? false
          const best = row.stores[0].price
          const shown = open ? row.stores : row.stores.slice(0, TOP_STORES)
          return (
            <div key={capacity} className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
              <p className="flex items-baseline justify-between text-sm">
                <span className="font-medium">{capacityLabel(capacity)}</span>
                <span className="text-xs text-slate-500">{text.stores(row.stores.length)}</span>
              </p>
              <ol className="mt-2 space-y-1.5">
                {shown.map((store, index) => (
                  <li key={store.store} className="flex items-center justify-between gap-2 text-sm">
                    <span className="flex min-w-0 items-center gap-2">
                      <span className={`w-5 shrink-0 text-right text-xs tabular-nums ${index === 0 ? 'font-semibold text-emerald-300' : 'text-slate-500'}`}>{index + 1}</span>
                      <span className={`truncate ${index === 0 ? 'text-emerald-200' : 'text-slate-200'}`} title={text.quotedAt(japanTime(store.collected_at))}>{store.store}</span>
                    </span>
                    <span className="flex shrink-0 items-baseline gap-2">
                      <Money amount={store.price} from={data.currency} to={currency} rates={rates} compact />
                      {index > 0 && <Diff amount={store.price} official={best} from={data.currency} to={currency} rates={rates} />}
                    </span>
                  </li>
                ))}
              </ol>
              {row.stores.length > TOP_STORES && (
                <button type="button" onClick={() => setExpanded({ ...expanded, [capacity]: !open })} className="mt-2 text-xs font-medium text-emerald-300 hover:text-emerald-200">
                  {open ? text.showFewerStores : text.showAllStores(row.stores.length)}
                </button>
              )}
              <p className="mt-2 text-[11px] text-slate-500">{text.quotedAt(japanTime(row.stores[0].collected_at))}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
