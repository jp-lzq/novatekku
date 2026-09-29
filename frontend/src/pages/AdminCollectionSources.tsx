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
}

const kindLabels: Record<string, string> = { official: '公式サイト', sheet: '表データ', apple_retail: 'Apple 定価' }
const statusStyles: Record<string, string> = {
  success: 'bg-emerald-50 text-emerald-700',
  partial: 'bg-amber-50 text-amber-700',
  failed: 'bg-rose-50 text-rose-700',
  unsupported: 'bg-slate-100 text-slate-500',
  running: 'bg-sky-50 text-sky-700',
}

export default function AdminCollectionSources() {
  const access = useAdminAccess()
  const sources = useQuery({
    queryKey: ['admin-collection-sources'],
    queryFn: () => apiGet<{ items: CollectionSource[] }>('/api/v1/admin/collection-sources'),
    enabled: access.data?.is_admin === true,
  })
  const items = sources.data?.items ?? []
  const failing = items.filter((item) => item.enabled && item.last_run?.status === 'failed').length

  return (
    <AdminShell title="収集元">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="text-xs font-semibold tracking-[0.18em] text-violet-600">COLLECTION SOURCES</p><h1 className="mt-2 text-2xl font-semibold">収集元と最新の収集結果</h1></div>
        <p className="text-sm text-slate-500">{sources.data ? `${items.length}件・直近失敗 ${failing}件` : '—'}</p>
      </div>
      <p className="mt-3 text-sm text-slate-500">収集元の追加・変更はサーバーのコマンドで行います（この画面は閲覧のみ）。</p>

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
                  <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${statusStyles[run?.status ?? ''] ?? 'bg-slate-100 text-slate-500'}`}>{run?.status ?? '未実行'}</span>
                </div>
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                  <span>最新：{dateTime(run?.started_at)}</span>
                  <span>最終成功：{dateTime(source.last_success_at)}</span>
                  {run && <span>取得 {run.items_found}件 / 保存 {run.prices_saved}件</span>}
                  <span>URL {source.urls.length}件</span>
                </div>
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
