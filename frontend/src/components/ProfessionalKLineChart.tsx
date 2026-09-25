import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  type UTCTimestamp,
} from 'lightweight-charts'
import { apiGet } from '../lib/api'
import type { Language } from '../i18n'

type Interval = '1h' | '1d' | '1w'

interface Candle {
  time: string
  label: string
  open: number
  high: number
  low: number
  close: number
  average: number
  best_store: string | null
  sample_count: number
  raw_sample_count: number
  store_count: number
  raw_store_count: number
  filtered_store_count: number
}

interface StorePoint {
  time: string
  label: string
  price: number
}

interface StoreSeries {
  store_id: number
  store_name: string
  latest_price: number
  points: StorePoint[]
}

interface IndicatorPoint {
  time: string
  value: number
}

interface AveragePoint extends IndicatorPoint {
  label: string
  store_count: number
}

interface AdvancedKLineResponse {
  product_id: number
  interval: Interval
  days: number
  candles: Candle[]
  average_series: AveragePoint[]
  store_series: StoreSeries[]
  indicators: {
    sma7: IndicatorPoint[]
    sma25: IndicatorPoint[]
    bb_upper: IndicatorPoint[]
    bb_lower: IndicatorPoint[]
    rsi14: IndicatorPoint[]
    macd: IndicatorPoint[]
    macd_signal: IndicatorPoint[]
    macd_histogram: IndicatorPoint[]
  }
  summary: {
    latest_close: number | null
    latest_average: number | null
    latest_filtered_store_count: number
    change: number
    change_percent: number
    high: number | null
    low: number | null
    store_count: number
    sample_count: number
    raw_sample_count: number
    data_points: number
    filtered_points: number
    filtered_store_points: number
  }
}

interface ProfessionalKLineChartProps {
  productId: number
  language: Language
}

const INTERVAL_DEFAULT_DAYS: Record<Interval, number> = {
  '1h': 7,
  '1d': 60,
  '1w': 180,
}

const RANGE_OPTIONS: Record<Interval, number[]> = {
  '1h': [7, 14, 30],
  '1d': [30, 60, 90, 180],
  '1w': [90, 180, 365],
}

const STORE_COLORS = [
  '#38bdf8',
  '#f97316',
  '#a78bfa',
  '#22c55e',
  '#f43f5e',
  '#eab308',
  '#14b8a6',
  '#fb7185',
  '#60a5fa',
  '#c084fc',
  '#84cc16',
  '#f59e0b',
  '#06b6d4',
  '#ec4899',
  '#10b981',
  '#818cf8',
  '#facc15',
  '#2dd4bf',
  '#fb923c',
  '#93c5fd',
  '#d946ef',
  '#4ade80',
  '#f87171',
  '#67e8f9',
]

const TEXT: Record<Language, Record<string, string>> = {
  ja: {
    title: 'TradingView 価格K線',
    subtitle: '相場から大きく外れた店舗を除外し、有効な価格推移を高速表示',
    intervalHour: '1時間',
    intervalDay: '日足',
    intervalWeek: '週足',
    storeLines: '店舗ライン',
    movingAverage: '移動平均 (SMA)',
    bollinger: 'BB',
    change: '変動',
    high: '高値',
    low: '安値',
    stores: '有効店舗',
    points: 'データ',
    loading: '読み込み中...',
    noData: '履歴データがありません',
    bestStore: '最高値店舗',
    samples: '取得数',
    indicators: 'テクニカル指標',
    effectiveAverage: '有効平均値',
    excluded: '除外店舗',
  },
  zh: {
    title: 'TradingView 价格K线',
    subtitle: '排除明显偏离市场的店铺，快速显示有效价格走势',
    intervalHour: '小时K',
    intervalDay: '日K',
    intervalWeek: '周K',
    storeLines: '店铺线',
    movingAverage: '移动平均 (SMA)',
    bollinger: 'BB',
    change: '变动',
    high: '高点',
    low: '低点',
    stores: '有效店铺',
    points: '数据',
    loading: '载入中...',
    noData: '没有历史数据',
    bestStore: '最高价店铺',
    samples: '采样',
    indicators: '技术指标',
    effectiveAverage: '有效均价',
    excluded: '排除店铺',
  },
  en: {
    title: 'TradingView Price K-Line',
    subtitle: 'Fast valid-price chart with clear market outliers excluded',
    intervalHour: '1H',
    intervalDay: '1D',
    intervalWeek: '1W',
    storeLines: 'Store Lines',
    movingAverage: 'Moving average (SMA)',
    bollinger: 'BB',
    change: 'Change',
    high: 'High',
    low: 'Low',
    stores: 'Valid stores',
    points: 'Points',
    loading: 'Loading...',
    noData: 'No history data',
    bestStore: 'Best store',
    samples: 'Samples',
    indicators: 'Indicators',
    effectiveAverage: 'Valid average',
    excluded: 'Excluded stores',
  },
}

function cx(...items: Array<string | false | null | undefined>) {
  return items.filter(Boolean).join(' ')
}

function formatPrice(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `¥${Math.round(value).toLocaleString()}`
}

function formatChange(value: number, percent: number) {
  if (!value) return '0'
  const sign = value > 0 ? '+' : '-'
  return `${sign}¥${Math.abs(Math.round(value)).toLocaleString()} (${sign}${Math.abs(percent).toFixed(2)}%)`
}

function toChartTime(value: string): UTCTimestamp {
  const normalized = /^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T00:00:00+09:00` : value
  return Math.floor(Date.parse(normalized) / 1000) as UTCTimestamp
}

function chartLocale(language: Language) {
  if (language === 'zh') return 'zh-CN'
  if (language === 'en') return 'en-US'
  return 'ja-JP'
}

export default function ProfessionalKLineChart({ productId, language }: ProfessionalKLineChartProps) {
  const labels = TEXT[language] ?? TEXT.ja
  const [interval, setInterval] = useState<Interval>('1d')
  const [days, setDays] = useState(INTERVAL_DEFAULT_DAYS['1d'])
  const [showStores, setShowStores] = useState(true)
  const [showEffectiveAverage, setShowEffectiveAverage] = useState(true)
  const [showMovingAverage, setShowMovingAverage] = useState(true)
  const [showBollinger, setShowBollinger] = useState(true)
  const [hoveredCandle, setHoveredCandle] = useState<Candle | null>(null)
  const chartContainerRef = useRef<HTMLDivElement | null>(null)

  const { data, isLoading } = useQuery<AdvancedKLineResponse>({
    queryKey: ['price-kline-advanced', productId, interval, days],
    queryFn: async () => {
      return apiGet<AdvancedKLineResponse>(`/api/v1/prices/kline-advanced/${productId}`, {
        params: { interval, days },
      })
    },
    staleTime: 1000 * 60 * 5,
  })

  useEffect(() => {
    const container = chartContainerRef.current
    if (!container || !data || data.candles.length === 0) return

    const candleByTime = new Map<number, Candle>()
    for (const candle of data.candles) candleByTime.set(Number(toChartTime(candle.time)), candle)

    const chart = createChart(container, {
      autoSize: true,
      height: 610,
      layout: {
        background: { type: ColorType.Solid, color: '#020617' },
        textColor: '#94a3b8',
        panes: {
          separatorColor: '#1e293b',
          separatorHoverColor: '#334155',
          enableResize: true,
        },
      },
      grid: {
        vertLines: { color: '#0f1d32' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        mode: CrosshairMode.MagnetOHLC,
        vertLine: { color: '#94a3b8', style: LineStyle.Dashed, labelBackgroundColor: '#334155' },
        horzLine: { color: '#94a3b8', style: LineStyle.Dashed, labelBackgroundColor: '#334155' },
      },
      rightPriceScale: {
        borderColor: '#334155',
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: interval === '1h',
        secondsVisible: false,
        rightOffset: 3,
        barSpacing: interval === '1h' ? 8 : 12,
        minBarSpacing: 3,
      },
      handleScroll: true,
      handleScale: true,
      localization: {
        locale: chartLocale(language),
        priceFormatter: (price: number) => `¥${Math.round(price).toLocaleString(chartLocale(language))}`,
      },
    })

    const candles = chart.addSeries(
      CandlestickSeries,
      {
        upColor: '#16a34a',
        downColor: '#dc2626',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
        priceLineVisible: false,
        lastValueVisible: false,
      },
      0,
    )
    candles.setData(
      data.candles.map((candle) => ({
        time: toChartTime(candle.time),
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })),
    )

    if (showStores) {
      data.store_series.forEach((store, index) => {
        const line = chart.addSeries(
          LineSeries,
          {
            color: `${STORE_COLORS[index % STORE_COLORS.length]}99`,
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          },
          0,
        )
        line.setData(store.points.map((point) => ({ time: toChartTime(point.time), value: point.price })))
      })
    }

    if (showBollinger) {
      const upper = chart.addSeries(
        LineSeries,
        { color: '#64748b', lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false },
        0,
      )
      const lower = chart.addSeries(
        LineSeries,
        { color: '#64748b', lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false },
        0,
      )
      upper.setData(data.indicators.bb_upper.map((point) => ({ time: toChartTime(point.time), value: point.value })))
      lower.setData(data.indicators.bb_lower.map((point) => ({ time: toChartTime(point.time), value: point.value })))
    }

    if (showEffectiveAverage) {
      const average = chart.addSeries(
        LineSeries,
        {
          color: '#2dd4bf',
          lineWidth: 3,
          title: labels.effectiveAverage,
          priceLineVisible: true,
          priceLineColor: '#2dd4bf',
          lastValueVisible: true,
        },
        0,
      )
      average.setData(data.average_series.map((point) => ({ time: toChartTime(point.time), value: point.value })))
    }

    if (showMovingAverage) {
      const sma7 = chart.addSeries(
        LineSeries,
        { color: '#facc15', lineWidth: 2, title: 'SMA 7', priceLineVisible: false, lastValueVisible: false },
        0,
      )
      const sma25 = chart.addSeries(
        LineSeries,
        { color: '#38bdf8', lineWidth: 2, title: 'SMA 25', priceLineVisible: false, lastValueVisible: false },
        0,
      )
      sma7.setData(data.indicators.sma7.map((point) => ({ time: toChartTime(point.time), value: point.value })))
      sma25.setData(data.indicators.sma25.map((point) => ({ time: toChartTime(point.time), value: point.value })))
    }

    const rsi = chart.addSeries(
      LineSeries,
      { color: '#a78bfa', lineWidth: 2, title: 'RSI 14', priceLineVisible: false, lastValueVisible: true },
      1,
    )
    rsi.setData(data.indicators.rsi14.map((point) => ({ time: toChartTime(point.time), value: point.value })))
    rsi.createPriceLine({ price: 70, color: '#475569', lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true })
    rsi.createPriceLine({ price: 30, color: '#475569', lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true })

    const histogram = chart.addSeries(
      HistogramSeries,
      { priceLineVisible: false, lastValueVisible: false, base: 0 },
      2,
    )
    histogram.setData(
      data.indicators.macd_histogram.map((point) => ({
        time: toChartTime(point.time),
        value: point.value,
        color: point.value >= 0 ? '#22c55e88' : '#ef444488',
      })),
    )
    const macd = chart.addSeries(
      LineSeries,
      { color: '#38bdf8', lineWidth: 2, title: 'MACD', priceLineVisible: false, lastValueVisible: false },
      2,
    )
    const signal = chart.addSeries(
      LineSeries,
      { color: '#f97316', lineWidth: 2, title: 'Signal', priceLineVisible: false, lastValueVisible: false },
      2,
    )
    macd.setData(data.indicators.macd.map((point) => ({ time: toChartTime(point.time), value: point.value })))
    signal.setData(data.indicators.macd_signal.map((point) => ({ time: toChartTime(point.time), value: point.value })))

    const panes = chart.panes()
    panes[0]?.setStretchFactor(4)
    panes[1]?.setStretchFactor(1)
    panes[2]?.setStretchFactor(1)

    chart.timeScale().fitContent()
    chart.subscribeCrosshairMove((param) => {
      if (param.time === undefined || param.point === undefined) {
        setHoveredCandle(null)
        return
      }
      setHoveredCandle(candleByTime.get(Number(param.time)) ?? null)
    })

    return () => {
      setHoveredCandle(null)
      chart.remove()
    }
  }, [data, interval, labels.effectiveAverage, language, showBollinger, showEffectiveAverage, showMovingAverage, showStores])

  const setActiveInterval = (nextInterval: Interval) => {
    setInterval(nextInterval)
    setDays(INTERVAL_DEFAULT_DAYS[nextInterval])
    setHoveredCandle(null)
  }

  if (isLoading || data === undefined) {
    return (
      <div className="flex h-80 items-center justify-center rounded-lg bg-slate-950 text-slate-300">
        <div className="mr-3 h-6 w-6 animate-spin rounded-full border-2 border-slate-600 border-t-sky-400" />
        <span>{labels.loading}</span>
      </div>
    )
  }

  if (data.candles.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center rounded-lg bg-slate-950 text-slate-400">
        {labels.noData}
      </div>
    )
  }

  const activeCandle = hoveredCandle ?? data.candles[data.candles.length - 1]
  const activeChangeClass =
    data.summary.change > 0 ? 'text-emerald-400' : data.summary.change < 0 ? 'text-red-400' : 'text-slate-300'

  return (
    <div className="overflow-hidden rounded-lg bg-slate-950 text-white">
      <div className="flex flex-col gap-4 border-b border-slate-800 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-sky-300">{labels.title}</p>
          <p className="mt-1 break-words text-xs text-slate-400">{labels.subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {([
            ['1h', labels.intervalHour],
            ['1d', labels.intervalDay],
            ['1w', labels.intervalWeek],
          ] as Array<[Interval, string]>).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setActiveInterval(value)}
              className={cx(
                'rounded border px-3 py-1.5 text-xs font-medium transition-colors',
                interval === value
                  ? 'border-sky-400 bg-sky-400 text-slate-950'
                  : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500',
              )}
            >
              {label}
            </button>
          ))}
          {RANGE_OPTIONS[interval].map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => {
                setDays(value)
                setHoveredCandle(null)
              }}
              className={cx(
                'rounded border px-2.5 py-1.5 text-xs font-medium transition-colors',
                days === value
                  ? 'border-emerald-400 bg-emerald-400 text-slate-950'
                  : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500',
              )}
            >
              {value}D
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 border-b border-slate-800 px-4 py-3 sm:grid-cols-6">
        <Metric label={labels.effectiveAverage} value={formatPrice(data.summary.latest_average)} />
        <Metric label={labels.change} value={formatChange(data.summary.change, data.summary.change_percent)} valueClass={activeChangeClass} />
        <Metric label={labels.high} value={formatPrice(data.summary.high)} />
        <Metric label={labels.low} value={formatPrice(data.summary.low)} />
        <Metric label={labels.stores} value={`${data.summary.store_count}`} />
        <Metric label={labels.excluded} value={`${data.summary.latest_filtered_store_count}`} />
      </div>

      <div className="flex flex-wrap items-center gap-2 px-4 pt-4">
        <ToggleButton active={showStores} onClick={() => setShowStores((value) => !value)} label={labels.storeLines} />
        <ToggleButton
          active={showEffectiveAverage}
          onClick={() => setShowEffectiveAverage((value) => !value)}
          label={labels.effectiveAverage}
        />
        <ToggleButton
          active={showMovingAverage}
          onClick={() => setShowMovingAverage((value) => !value)}
          label={labels.movingAverage}
        />
        <ToggleButton active={showBollinger} onClick={() => setShowBollinger((value) => !value)} label={labels.bollinger} />
        <span className="ml-auto text-xs text-slate-500">
          {labels.points}: {data.summary.data_points} / {labels.samples}: {data.summary.sample_count}
        </span>
      </div>

      <div className="relative mt-2 min-h-[610px] w-full" aria-label={labels.title} role="img">
        <div ref={chartContainerRef} className="h-[610px] w-full" />
        <div className="pointer-events-none absolute left-3 top-3 z-10 max-w-[calc(100%-5rem)] rounded border border-slate-700/80 bg-slate-900/90 px-3 py-2 text-[11px] shadow-lg backdrop-blur sm:left-4 sm:text-xs">
          <p className="truncate font-semibold text-slate-100">{activeCandle.label}</p>
          <p className="mt-1 whitespace-nowrap text-slate-400">
            O {formatPrice(activeCandle.open)} H {formatPrice(activeCandle.high)} L {formatPrice(activeCandle.low)} C{' '}
            {formatPrice(activeCandle.close)}
          </p>
          <p className="mt-1 text-teal-300">
            {labels.effectiveAverage}: {formatPrice(activeCandle.average)}
          </p>
          <p className="mt-1 truncate text-slate-400">
            {labels.bestStore}: {activeCandle.best_store ?? '-'} / {labels.stores}: {activeCandle.store_count} / {labels.excluded}:{' '}
            {activeCandle.filtered_store_count}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-800 px-4 py-2 text-[11px] text-slate-500">
        <span><span className="text-teal-400">━</span> {labels.effectiveAverage}</span>
        <span><span className="text-yellow-400">━</span> SMA 7</span>
        <span><span className="text-sky-400">━</span> SMA 25 / MACD</span>
        <span><span className="text-violet-400">━</span> RSI 14</span>
        <span className="ml-auto">
          Copyright © 2025 TradingView, Inc.{' '}
          <a
            href="https://www.tradingview.com/"
            target="_blank"
            rel="noreferrer"
            className="pointer-events-auto text-sky-400 hover:text-sky-300"
          >
            TradingView
          </a>
        </span>
      </div>

      {data.store_series.length > 0 && (
        <div className="max-h-32 overflow-y-auto border-t border-slate-800 px-4 py-3">
          <div className="flex flex-wrap gap-x-4 gap-y-2">
            {data.store_series.map((series, index) => (
              <div key={series.store_id} className="flex min-w-0 items-center gap-2 text-xs text-slate-300">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: STORE_COLORS[index % STORE_COLORS.length] }}
                />
                <span className="max-w-[9rem] truncate">{series.store_name}</span>
                <span className="font-medium text-slate-100">{formatPrice(series.latest_price)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ToggleButton({
  active,
  onClick,
  label,
}: {
  active: boolean
  onClick: () => void
  label: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'rounded border px-3 py-1.5 text-xs font-medium transition-colors',
        active ? 'border-slate-200 bg-slate-200 text-slate-950' : 'border-slate-700 bg-slate-900 text-slate-300 hover:border-slate-500',
      )}
    >
      {label}
    </button>
  )
}

function Metric({ label, value, valueClass }: { label: string; value: string; valueClass?: string }) {
  return (
    <div className="min-w-0 rounded border border-slate-800 bg-slate-900 px-3 py-2">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={cx('mt-1 truncate text-sm font-semibold text-slate-100 sm:text-base', valueClass)}>{value}</p>
    </div>
  )
}
