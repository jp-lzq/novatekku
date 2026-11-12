import { useQuery } from '@tanstack/react-query'
import AdminShell, { dateTime, useAdminAccess } from '../components/AdminShell'
import { apiGet } from '../lib/api'

interface CollectionRunSummary {
  status: string
  started_at: string
  finished_at?: string | null
  items_found: number
  prices_saved: number
  error_message?: string | null
}

type HealthState = 'failing' | 'stale' | 'degraded' | 'unknown' | 'healthy' | 'unsupported' | 'disabled'

interface SourceHealth {
  state: HealthState
  reasons: string[]
  consecutive_failures: number
  runs_in_window: number
  success_rate: number | null
  empty_page_ratio: number | null
}

interface CollectionSource {
  id: number
  kind: string
  name: string
  store_name?: string | null
  parser?: string | null
  urls: string[]
  public_url?: string | null
  unsupported_reason?: string | null
  enabled: boolean
  updated_at: string
  last_run?: CollectionRunSummary | null
  last_success_at?: string | null
  health?: SourceHealth
}

const kindLabels: Record<string, string> = { official: '公式サイト', sheet: '表データ', apple_retail: 'Apple 定価', market: '海外市場' }
const statusStyles: Record<string, string> = {
  success: 'bg-emerald-50 text-emerald-700',
  partial: 'bg-amber-50 text-amber-700',
  failed: 'bg-rose-50 text-rose-700',
  unsupported: 'bg-slate-100 text-slate-500',
  running: 'bg-sky-50 text-sky-700',
}

// worst first; the same order the summary uses
const healthStyles: Record<HealthState, { label: string; tone: string }> = {
  failing: { label: '連続失敗', tone: 'bg-rose-600 text-white' },
  stale: { label: '長時間成功なし', tone: 'bg-rose-50 text-rose-700' },
  degraded: { label: '要確認', tone: 'bg-amber-50 text-amber-700' },
  unknown: { label: '未収集', tone: 'bg-slate-100 text-slate-500' },
  healthy: { label: '正常', tone: 'bg-emerald-50 text-emerald-700' },
  unsupported: { label: '未対応', tone: 'bg-slate-100 text-slate-500' },
  disabled: { label: '停止中', tone: 'bg-slate-100 text-slate-500' },
}
const healthOrder = Object.keys(healthStyles) as HealthState[]

function HealthBadge({ health }: { health?: SourceHealth }) {
  if (!health) return null
  const style = healthStyles[health.state]
  return <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${style.tone}`}>{style.label}</span>
}

export default function AdminCollectionSources() {
  const access = useAdminAccess()
  const sources = useQuery({
    queryKey: ['admin-collection-sources'],
    queryFn: () => apiGet<{ items: CollectionSource[] }>('/api/v1/admin/collection-sources'),
    enabled: access.data?.is_admin === true,
  })
  // problem sources first, so a failing store is never buried in the list
  const items = [...(sources.data?.items ?? [])].sort(
    (a, b) => healthOrder.indexOf(a.health?.state ?? 'healthy') - healthOrder.indexOf(b.health?.state ?? 'healthy'),
  )
  const failing = items.filter((item) => item.enabled && item.last_run?.status === 'failed').length
  const problems = items.filter((item) => ['failing', 'stale', 'degraded'].includes(item.health?.state ?? ''))

  return (
    <AdminShell title="収集元">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-xs font-semibold tracking-[0.18em] text-violet-600">COLLECTION SOURCES</p><h1 className="mt-2 text-2xl font-semibold">収集元と最新の収集結果</h1></div>
        <p className="text-sm text-slate-500">{sources.data ? `${items.length}件・直近失敗 ${failing}件` : '—'}</p>
      </div>
      <p className="mt-3 text-sm text-slate-500">収集元の追加・変更はサーバーのコマンドで行います（この画面は閲覧のみ）。</p>

      {sources.data && (
        <section className={`mt-5 rounded-2xl border p-4 ${problems.length ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'}`}>
          <p className="text-sm font-semibold">{problems.length ? `確認が必要な収集元 ${problems.length}件` : 'すべての収集元が正常に動いています'}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {healthOrder.filter((state) => items.some((item) => item.health?.state === state)).map((state) => (
              <span key={state} className={`rounded-full px-2.5 py-1 font-medium ${healthStyles[state].tone}`}>
                {healthStyles[state].label} {items.filter((item) => item.health?.state === state).length}
              </span>
            ))}
          </div>
          {problems.length > 0 && (
            <ul className="mt-3 space-y-1 text-sm text-slate-700">
              {problems.map((item) => <li key={item.id}>{item.store_name || item.name}：{item.health?.reasons.join('、')}</li>)}
            </ul>
          )}
        </section>
      )}

      <section className="mt-5 space-y-3">
        {sources.isLoading && <p className="rounded-2xl bg-white p-5 text-sm text-slate-500">読み込み中...</p>}
        {sources.isError && <p className="rounded-2xl bg-white p-5 text-sm text-rose-600">収集元を取得できませんでした。</p>}
        {sources.data && items.length === 0 && <p className="rounded-2xl bg-white p-5 text-sm text-slate-500">収集元は登録されていません。</p>}
        {items.map((source) => {
          const run = source.last_run
          return (
            <details key={source.id} className={`rounded-2xl border border-slate-200 bg-white p-4 shadow-sm ${source.enabled ? '' : 'opacity-60'}`}>
              <summary className="cursor-pointer list-none">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-violet-700">{kindLabels[source.kind] ?? source.kind}{source.enabled ? '' : '・停止中'}</p>
                    <p className="mt-1 break-words font-medium">{source.store_name || source.name}</p>
                    <p className="text-xs text-slate-400">{source.name}</p>
                  </div>
                  <div className="flex shrink-0 gap-1.5">
                    <HealthBadge health={source.health} />
                    <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${statusStyles[run?.status ?? ''] ?? 'bg-slate-100 text-slate-500'}`}>{run?.status ?? '未実行'}</span>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                  <span>最新：{dateTime(run?.started_at)}</span>
                  <span>最終成功：{dateTime(source.last_success_at)}</span>
                  {run && <span>取得 {run.items_found}件 / 保存 {run.prices_saved}件</span>}
                  <span>URL {source.urls.length}件</span>
                  {source.health?.success_rate != null && <span>24時間の成功率 {Math.round(source.health.success_rate * 100)}%</span>}
                  {source.health?.empty_page_ratio != null && source.health.empty_page_ratio > 0 && <span>空ページ {Math.round(source.health.empty_page_ratio * 100)}%</span>}
                </div>
                {source.health && source.health.reasons.length > 0 && ['failing', 'stale', 'degraded'].includes(source.health.state) && (
                  <p className="mt-2 text-xs font-medium text-rose-700">{source.health.reasons.join('、')}</p>
                )}
              </summary>
              <div className="mt-4 space-y-2 border-t border-slate-100 pt-4 text-sm">
                {source.unsupported_reason && <p className="text-slate-500">対象外の理由：{source.unsupported_reason}</p>}
                {run?.error_message && <p className="break-words text-rose-600">エラー：{run.error_message}</p>}
                {source.parser && <p className="text-slate-500">解析方式：{source.parser}</p>}
                {source.public_url && <p className="break-all text-slate-500">公開ページ：{source.public_url}</p>}
                <ul className="space-y-1">
                  {source.urls.map((url) => <li key={url} className="break-all font-mono text-xs text-slate-600">{url}</li>)}
                </ul>
                <p className="text-xs text-slate-400">設定更新：{dateTime(source.updated_at)}</p>
              </div>
            </details>
          )
        })}
      </section>
    </AdminShell>
  )
}
