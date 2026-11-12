import { useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, CircleAlert, Search } from 'lucide-react'
import AdminShell, { useAdminAccess } from '../components/AdminShell'
import { apiGet } from '../lib/api'

type Language = 'ja' | 'zh' | 'en'

interface Device {
  model: string
  capacity: string | null
  color: string | null
  condition: string | null
  carrier: string | null
  quantity: number
  known: boolean
}

interface Understanding {
  intent: string
  confidence: number
  needs_prices: boolean
  markets: string[]
  devices: Device[]
  follow_up_capacity: string | null
  unknown_models: string[]
}

interface Finding {
  kind: 'unsupported_amount' | 'wrong_store_price'
  text: string
  store: string | null
  expected: number[]
}

interface AnswerCheck {
  status: 'ok' | 'warning' | 'no_evidence' | 'no_amounts'
  checked: number
  supported: number
  findings: Finding[]
}

interface PreviewResponse {
  understanding: Understanding
  price_evidence: { has_prices?: boolean; fx_updated?: string | null }
  lines: string[]
  answer_check?: AnswerCheck
}

// what each intent means, for people reading the page
const INTENT_LABELS: Record<string, string> = {
  price_quote: '買取価格',
  store_ranking: 'どの店が高いか',
  model_compare: '機種の比較',
  sell_timing: '売り時',
  overseas_market: '海外の価格',
  bulk_quote: 'まとめ売りの合計',
  catalog: '機種の一覧',
  retail_price: 'Apple 定価',
  store_info: '店舗情報',
  device_help: '使い方・設定',
  greeting: 'あいさつ',
  off_topic: '対象外の話題',
}

const CHECK_LABELS: Record<AnswerCheck['status'], { text: string; tone: string }> = {
  ok: { text: '回答の金額はすべて根拠と一致', tone: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
  warning: { text: '根拠で確認できない金額があります', tone: 'text-rose-700 bg-rose-50 border-rose-200' },
  no_evidence: { text: '照合できる価格の根拠がありません', tone: 'text-slate-600 bg-slate-50 border-slate-200' },
  no_amounts: { text: '回答に金額がありません', tone: 'text-slate-600 bg-slate-50 border-slate-200' },
}

const EXAMPLES = ['17プロマ 256 どこが一番高い？', '17 pro と 16 pro max どっちが高く売れる？', '16e×3 と 17 256×2 の合計', 'iPhone Duo 1TB 香港ならいくら？']

function DeviceCard({ device }: { device: Device }) {
  const details = [
    device.capacity && (/^\d+$/.test(device.capacity) ? `${device.capacity}GB` : device.capacity),
    device.color,
    device.condition,
    device.carrier,
    device.quantity > 1 ? `${device.quantity}台` : null,
  ].filter(Boolean)
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm">
      <p className="font-semibold">
        {device.model}
        {!device.known && <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-medium text-amber-700">対象外</span>}
      </p>
      <p className="mt-0.5 text-xs text-slate-500">{details.length ? details.join(' / ') : '容量・色の指定なし'}</p>
    </div>
  )
}

export default function AdminAIPreview() {
  const access = useAdminAccess()
  const [message, setMessage] = useState('')
  const [answer, setAnswer] = useState('')
  const [language, setLanguage] = useState<Language>('ja')
  const [submitted, setSubmitted] = useState<{ message: string; answer: string; language: Language } | null>(null)

  const preview = useQuery({
    queryKey: ['admin-ai-preview', submitted],
    queryFn: () =>
      apiGet<PreviewResponse>('/api/v1/ai/preview', {
        params: { message: submitted!.message, language: submitted!.language, ...(submitted!.answer ? { answer: submitted!.answer } : {}) },
      }),
    enabled: access.data?.is_admin === true && submitted !== null,
    retry: false,
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (message.trim()) setSubmitted({ message: message.trim(), answer: answer.trim(), language })
  }

  const data = preview.data
  const check = data?.answer_check

  return (
    <AdminShell title="AI プレビュー">
      <div>
        <p className="text-xs font-semibold tracking-[0.18em] text-violet-600">AI PREVIEW</p>
        <h1 className="mt-2 text-2xl font-semibold">質問の理解と価格の根拠</h1>
        <p className="mt-1 text-sm text-slate-500">本番データで、AI が質問をどう理解し、どの価格を根拠にするかを確認します。モデルは呼ばず、質問回数も減りません。</p>
      </div>

      <form onSubmit={submit} className="mt-6 space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="block text-sm font-medium" htmlFor="preview-message">質問</label>
        <div className="flex gap-2">
          <input
            id="preview-message"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            maxLength={2000}
            placeholder="例：17プロマ 256 どこが一番高い？"
            className="h-10 min-w-0 flex-1 rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-violet-400"
          />
          <select value={language} onChange={(event) => setLanguage(event.target.value as Language)} className="h-10 rounded-xl border border-slate-200 px-2 text-sm">
            <option value="ja">日本語</option>
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
          <button type="submit" className="inline-flex h-10 items-center gap-1.5 rounded-xl bg-slate-950 px-4 text-sm font-medium text-white disabled:opacity-40" disabled={!message.trim()}>
            <Search className="h-4 w-4" />確認
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <button key={example} type="button" onClick={() => setMessage(example)} className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-500 hover:border-violet-300 hover:text-slate-900">
              {example}
            </button>
          ))}
        </div>
        <label className="block pt-2 text-sm font-medium" htmlFor="preview-answer">AI の回答（任意：金額を根拠と照合します）</label>
        <textarea
          id="preview-answer"
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
          maxLength={8000}
          rows={3}
          placeholder="AI 記録などから回答を貼り付けると、回答中の金額と店舗の価格を確認します"
          className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-violet-400"
        />
      </form>

      {preview.isLoading && <p className="mt-6 rounded-2xl bg-white p-5 text-sm text-slate-500">確認中...</p>}
      {preview.isError && <p className="mt-6 rounded-2xl bg-white p-5 text-sm text-rose-600">プレビューを取得できませんでした。</p>}

      {data && (
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">質問の理解</h2>
            <p className="mt-2 text-lg font-semibold">
              {INTENT_LABELS[data.understanding.intent] ?? data.understanding.intent}
              <span className="ml-2 text-sm font-normal text-slate-400">確信度 {Math.round(data.understanding.confidence * 100)}%</span>
            </p>
            <div className="mt-3 space-y-2">
              {data.understanding.devices.length === 0 && <p className="text-sm text-slate-500">機種は見つかりませんでした。</p>}
              {data.understanding.devices.map((device, index) => <DeviceCard key={`${device.model}-${index}`} device={device} />)}
            </div>
            {data.understanding.markets.length > 0 && <p className="mt-3 text-xs text-slate-500">市場：{data.understanding.markets.join(' / ')}</p>}
            {data.understanding.follow_up_capacity && <p className="mt-1 text-xs text-slate-500">続きの質問の容量：{data.understanding.follow_up_capacity}</p>}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-500">価格の根拠（AI に渡す内容）</h2>
            {data.lines.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">この質問で使う価格はありません。</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {data.lines.map((line) => <li key={line} className="rounded-xl bg-slate-50 px-3 py-2 text-sm leading-6 text-slate-700">{line}</li>)}
              </ul>
            )}
            {data.price_evidence.fx_updated && <p className="mt-3 text-xs text-slate-400">為替の更新：{data.price_evidence.fx_updated.slice(0, 16).replace('T', ' ')}</p>}
          </section>

          {check && (
            <section className={`rounded-2xl border p-4 lg:col-span-2 ${CHECK_LABELS[check.status].tone}`}>
              <p className="flex items-center gap-2 font-semibold">
                {check.status === 'ok' ? <CheckCircle2 className="h-5 w-5" /> : <CircleAlert className="h-5 w-5" />}
                {CHECK_LABELS[check.status].text}
              </p>
              <p className="mt-1 text-sm">金額 {check.checked} 件のうち {check.supported} 件を確認</p>
              {check.findings.length > 0 && (
                <ul className="mt-2 space-y-1 text-sm">
                  {check.findings.map((finding, index) => (
                    <li key={`${finding.text}-${index}`}>
                      {finding.kind === 'wrong_store_price'
                        ? `${finding.store} は ${finding.text} ではなく ${finding.expected.map((value) => `${value.toLocaleString()}円`).join(' / ')}`
                        : `${finding.text} は根拠にない金額です`}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>
      )}
    </AdminShell>
  )
}
