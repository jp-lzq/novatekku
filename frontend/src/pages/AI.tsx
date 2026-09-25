import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Sparkles } from 'lucide-react'
import ProductNav from '../components/ProductNav'
import { apiGet, apiPost } from '../lib/api'
import { getCsrfHeaders } from '../lib/member'
import { useI18n, type Language } from '../i18n'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface AIChatResponse {
  reply: string
  remaining: number
}

const COPY: Record<Language, {
  eyebrow: string
  title: string
  lead: string
  examples: string[]
  databaseNote: string
  dataScale: string
}> = {
  en: {
    eyebrow: 'SMARTPHONE & PRICE INTELLIGENCE',
    title: 'What would you like to know?',
    lead: 'Ask about smartphones or analyze the latest local buyback prices.',
    examples: [
      'Which store pays the most for iPhone 17 Pro Max 256GB?',
      'Is now a good time to sell my iPhone?',
      'How do I move data from Android to iPhone?',
    ],
    databaseNote: 'Price answers use NOVA local market data.',
    dataScale: 'Latest data: 10M+ records · Historical data: 50M+ records (2020–2025)',
  },
  zh: {
    eyebrow: '手机知识与价格智能',
    title: '今天想了解什么？',
    lead: '可以问手机问题，也可以分析最新的本地回收价格。',
    examples: [
      'iPhone 17 Pro Max 256GB 现在哪家价格最高？',
      '现在适合卖掉我的 iPhone 吗？',
      '安卓手机怎么把数据转到 iPhone？',
    ],
    databaseNote: '价格回答使用 NOVA 本地市场数据。',
    dataScale: '最新数据记录数：1000万条+ · 历史数据记录数：5000万条+（2020–2025）',
  },
  ja: {
    eyebrow: 'スマートフォンと価格インテリジェンス',
    title: '今日は何を知りたいですか？',
    lead: 'スマートフォンの相談も、最新のローカル買取価格の分析もできます。',
    examples: [
      'iPhone 17 Pro Max 256GB は今どの店舗が一番高いですか？',
      '今はiPhoneを売る良いタイミングですか？',
      'AndroidからiPhoneへデータを移す方法は？',
    ],
    databaseNote: '価格の回答にはNOVAのローカル市場データを使用します。',
    dataScale: '最新データ収録件数：1,000万件+ · 履歴データ収録件数：5,000万件+（2020–2025）',
  },
}

export default function AI() {
  const { language, t } = useI18n()
  const copy = COPY[language]
  const [sessionId] = useState(() => crypto.randomUUID())
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [remaining, setRemaining] = useState(10)
  const [isLoading, setIsLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => {
    let active = true
    apiGet<{ remaining: number }>(`/api/v1/ai/usage`, { params: { session_id: sessionId } }).then((usage) => {
      if (!active) return
      setRemaining(usage.remaining)
    }).catch(() => undefined)
    return () => { active = false }
  }, [sessionId])

  const handleSend = async (rawContent = input) => {
    const content = rawContent.trim()
    if (!content || isLoading || remaining <= 0) return

    setMessages((previous) => [...previous, { id: `${Date.now()}-user`, role: 'user', content }])
    setInput('')
    setIsLoading(true)

    try {
      const data = await apiPost<AIChatResponse>(
        '/api/v1/ai/chat',
        { session_id: sessionId, message: content, language },
        { headers: getCsrfHeaders() },
      )
      setMessages((previous) => [
        ...previous,
        { id: `${Date.now()}-assistant`, role: 'assistant', content: data.reply || t('aiEmptyReply') },
      ])
      setRemaining(data.remaining)
    } catch (error: any) {
      const status = error?.response?.status
      setMessages((previous) => [
        ...previous,
        { id: `${Date.now()}-error`, role: 'assistant', content: status === 429 ? t('aiLimitReached') : t('aiError') },
      ])
      if (status === 429) setRemaining(0)
    } finally {
      setIsLoading(false)
    }
  }

  const chooseExample = (question: string) => {
    setInput(question)
    textareaRef.current?.focus()
  }

  return (
    <div className="flex min-h-[100dvh] flex-col bg-[#f7f7f8] text-slate-950">
      <ProductNav />

      <main className="relative flex flex-1 flex-col overflow-hidden">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-80"
          style={{ background: 'radial-gradient(circle at 50% 0%, rgba(221, 214, 254, 0.48), transparent 68%)' }}
        />

        {messages.length === 0 ? (
          <section className="relative mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center px-4 pb-8 pt-14 sm:px-6">
            <div className="text-center">
              <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-slate-950 text-white shadow-xl shadow-slate-300">
                <Sparkles className="h-5 w-5" />
              </div>
              <p className="mt-6 text-[10px] font-semibold tracking-[0.22em] text-slate-400 sm:text-xs">{copy.eyebrow}</p>
              <h1 className="mt-4 text-3xl font-medium tracking-[-0.04em] sm:text-5xl">{copy.title}</h1>
              <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-slate-500 sm:text-base">{copy.lead}</p>
            </div>

            <div className="mx-auto mt-9 w-full max-w-3xl">
              <Composer
                input={input}
                setInput={setInput}
                textareaRef={textareaRef}
                onSend={() => handleSend()}
                disabled={remaining <= 0 || isLoading}
                placeholder={remaining > 0 ? t('inputPlaceholder') : t('noQuestionsLeft')}
              />
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {copy.examples.map((question) => (
                  <button key={question} type="button" onClick={() => chooseExample(question)} className="rounded-full border border-black/[0.08] bg-white/80 px-3.5 py-2 text-left text-xs text-slate-500 shadow-sm transition-colors hover:border-slate-300 hover:text-slate-950">
                    {question}
                  </button>
                ))}
              </div>
              <p className="mt-5 text-center text-[11px] leading-5 text-slate-400">{copy.databaseNote}<br className="sm:hidden" /> {copy.dataScale} · {t('remainingCount', { count: remaining })}</p>
            </div>
          </section>
        ) : (
          <section className="relative mx-auto flex w-full max-w-4xl flex-1 flex-col px-4 sm:px-6">
            <div className="flex-1 space-y-8 py-10 sm:py-14">
              {messages.map((message) => (
                <article key={message.id} className="grid grid-cols-[36px_1fr] gap-3 sm:grid-cols-[42px_1fr] sm:gap-4">
                  <div className={`grid h-9 w-9 place-items-center rounded-xl text-xs font-semibold sm:h-10 sm:w-10 ${message.role === 'user' ? 'bg-white text-slate-500 ring-1 ring-slate-200' : 'bg-slate-950 text-white'}`}>
                    {message.role === 'user' ? 'YOU' : 'N'}
                  </div>
                  <div className={`min-w-0 rounded-2xl px-4 py-3.5 sm:px-5 ${message.role === 'user' ? 'bg-white ring-1 ring-black/[0.06]' : 'bg-transparent'}`}>
                    <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-700 sm:text-base sm:leading-8">{message.content}</p>
                  </div>
                </article>
              ))}
              {isLoading && (
                <div className="grid grid-cols-[36px_1fr] gap-3 sm:grid-cols-[42px_1fr] sm:gap-4">
                  <div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-950 text-xs font-semibold text-white sm:h-10 sm:w-10">N</div>
                  <div className="flex items-center gap-1.5 px-4 py-4">
                    {[0, 150, 300].map((delay) => <span key={delay} className="h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: `${delay}ms` }} />)}
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            <div className="sticky bottom-0 bg-gradient-to-t from-[#f7f7f8] via-[#f7f7f8] to-transparent pb-5 pt-8">
              <Composer
                input={input}
                setInput={setInput}
                textareaRef={textareaRef}
                onSend={() => handleSend()}
                disabled={remaining <= 0 || isLoading}
                placeholder={remaining > 0 ? t('inputPlaceholder') : t('noQuestionsLeft')}
              />
              <p className="mt-2 text-center text-[10px] leading-4 text-slate-400">{copy.databaseNote}<br className="sm:hidden" /> {copy.dataScale} · {t('remainingCount', { count: remaining })}</p>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

function Composer({
  input,
  setInput,
  textareaRef,
  onSend,
  disabled,
  placeholder,
}: {
  input: string
  setInput: (value: string) => void
  textareaRef: React.RefObject<HTMLTextAreaElement>
  onSend: () => void
  disabled: boolean
  placeholder: string
}) {
  return (
    <div className="flex items-end gap-2 rounded-[24px] border border-black/[0.09] bg-white p-2.5 shadow-[0_18px_60px_rgba(15,23,42,0.12)] focus-within:border-slate-300">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(event) => setInput(event.target.value.slice(0, 2000))}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault()
            onSend()
          }
        }}
        rows={1}
        maxLength={2000}
        disabled={disabled}
        placeholder={placeholder}
        className="max-h-36 min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed sm:text-base"
      />
      <button
        type="button"
        onClick={onSend}
        disabled={disabled || !input.trim()}
        aria-label="Send"
        className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-slate-950 text-white transition-colors hover:bg-violet-700 disabled:bg-slate-200 disabled:text-slate-400"
      >
        <ArrowUp className="h-5 w-5" />
      </button>
    </div>
  )
}
