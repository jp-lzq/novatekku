import { useEffect, useRef, useState } from 'react'
import { Send, Sparkles, X } from 'lucide-react'
import { apiPost } from '../lib/api'
import { useI18n, type Language } from '../i18n'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface AIChatResponse {
  reply: string
  remaining: number
}

const COPY: Record<Language, { subtitle: string; examples: string[]; note: string }> = {
  en: {
    subtitle: 'Smartphone and local price assistant',
    examples: [
      'Which store pays the most for iPhone 17 Pro Max 256GB?',
      'How do I move data from Android to iPhone?',
      'Why is my phone battery draining so quickly?',
    ],
    note: 'NOVA prices come from the local price database.',
  },
  zh: {
    subtitle: '手机知识与本地价格助手',
    examples: [
      'iPhone 17 Pro Max 256GB 现在哪家价格最高？',
      '安卓手机怎么把数据转到 iPhone？',
      '手机电池掉电很快，应该怎么检查？',
    ],
    note: '回收价格读取 NOVA 本地价格数据库。',
  },
  ja: {
    subtitle: 'スマホ相談・ローカル価格アシスタント',
    examples: [
      'iPhone 17 Pro Max 256GB は今どの店舗が一番高いですか？',
      'Android から iPhone へデータを移す方法は？',
      'スマホのバッテリー消費が早い原因を教えてください。',
    ],
    note: '買取価格は NOVA のローカル価格データベースを参照します。',
  },
}

export default function AIChat() {
  const { language, t } = useI18n()
  const copy = COPY[language]
  const [isOpen, setIsOpen] = useState(false)
  const [sessionId] = useState(() => crypto.randomUUID())
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: t('aiWelcome'),
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [remaining, setRemaining] = useState(10)
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : ''
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  useEffect(() => {
    setMessages((previous) => {
      if (previous.length !== 1 || previous[0]?.id !== 'welcome') return previous
      return [{ id: 'welcome', role: 'assistant', content: t('aiWelcome'), timestamp: new Date() }]
    })
  }, [language, t])

  const handleSend = async (rawContent: string) => {
    const content = rawContent.trim()
    if (!content || remaining <= 0 || isLoading) return

    setMessages((previous) => [
      ...previous,
      { id: `${Date.now()}-user`, role: 'user', content, timestamp: new Date() },
    ])
    setInput('')
    setIsLoading(true)

    try {
      const data = await apiPost<AIChatResponse>('/api/v1/ai/chat', {
        session_id: sessionId,
        message: content,
        language,
      })
      setMessages((previous) => [
        ...previous,
        {
          id: `${Date.now()}-assistant`,
          role: 'assistant',
          content: data.reply || t('aiEmptyReply'),
          timestamp: new Date(),
        },
      ])
      setRemaining(data.remaining)
    } catch (error: any) {
      const status = error?.response?.status
      setMessages((previous) => [
        ...previous,
        {
          id: `${Date.now()}-error`,
          role: 'assistant',
          content: status === 429 ? t('aiLimitReached') : t('aiError'),
          timestamp: new Date(),
        },
      ])
      if (status === 429) setRemaining(0)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 rounded-full bg-gradient-to-r from-violet-600 to-purple-600 px-4 py-2 text-white shadow-lg transition-all hover:scale-105 hover:shadow-xl"
      >
        <Sparkles className="h-4 w-4" />
        <span className="text-sm font-medium">NOVA AI</span>
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-3 backdrop-blur-sm sm:p-4">
          <div className="flex h-[88vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl sm:h-[80vh]">
            <div className="flex items-center justify-between border-b border-violet-500 bg-gradient-to-r from-violet-600 to-purple-600 px-4 py-4 sm:px-6">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/20">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-semibold text-white">NOVA AI</h3>
                  <p className="truncate text-xs text-white/80">{copy.subtitle}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 sm:gap-3">
                <span className="whitespace-nowrap rounded-full bg-white/20 px-3 py-1 text-xs text-white/90">
                  {t('remainingCount', { count: remaining })}
                </span>
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="rounded-full p-2 text-white/80 transition-colors hover:bg-white/20 hover:text-white"
                  aria-label={t('close')}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-4">
              {messages.map((message) => (
                <div key={message.id} className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                  <div
                    className={
                      message.role === 'user'
                        ? 'max-w-[88%] rounded-2xl rounded-br-md bg-violet-600 px-4 py-3 text-white sm:max-w-[80%]'
                        : 'max-w-[88%] rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-slate-800 shadow-sm sm:max-w-[80%]'
                    }
                  >
                    <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">{message.content}</p>
                    <span className={message.role === 'user' ? 'mt-1 block text-xs text-violet-200' : 'mt-1 block text-xs text-slate-400'}>
                      {message.timestamp.toLocaleTimeString(language === 'zh' ? 'zh-CN' : language === 'en' ? 'en-US' : 'ja-JP', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>
              ))}

              {messages.length === 1 && (
                <div className="pt-2">
                  <p className="mb-3 text-center text-xs text-slate-500">{t('aiExamplesTitle')}</p>
                  <div className="flex flex-col gap-2 sm:items-center">
                    {copy.examples.map((question) => (
                      <button
                        key={question}
                        type="button"
                        onClick={() => handleSend(question)}
                        disabled={remaining <= 0 || isLoading}
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-left text-xs text-slate-600 transition-colors hover:border-violet-400 hover:text-violet-600 disabled:opacity-50"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
                    <div className="flex gap-1">
                      {[0, 150, 300].map((delay) => (
                        <span
                          key={delay}
                          className="h-2 w-2 animate-bounce rounded-full bg-slate-400"
                          style={{ animationDelay: `${delay}ms` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-slate-200 bg-white p-3 sm:p-4">
              <div className="flex items-end gap-2">
                <div className="relative flex-1">
                  <textarea
                    value={input}
                    onChange={(event) => setInput(event.target.value.slice(0, 2000))}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault()
                        handleSend(input)
                      }
                    }}
                    placeholder={remaining > 0 ? t('inputPlaceholder') : t('noQuestionsLeft')}
                    disabled={remaining <= 0 || isLoading}
                    maxLength={2000}
                    rows={2}
                    className="max-h-32 min-h-14 w-full resize-y rounded-xl border border-slate-200 px-4 py-3 pr-16 text-sm focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-100 disabled:bg-slate-50 disabled:text-slate-400"
                  />
                  <span className="absolute bottom-2 right-3 text-[10px] text-slate-400">{input.length}/2000</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleSend(input)}
                  disabled={!input.trim() || remaining <= 0 || isLoading}
                  className="rounded-xl bg-violet-600 px-4 py-4 text-white transition-colors hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-slate-200"
                  aria-label={t('send')}
                >
                  <Send className="h-5 w-5" />
                </button>
              </div>
              <p className="mt-2 text-center text-xs text-slate-400">{copy.note}</p>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
