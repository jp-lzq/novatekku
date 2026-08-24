import { useState, useRef, useEffect } from 'react'
import { X, Send, Sparkles } from 'lucide-react'
import { apiGet } from '../lib/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

const DEFAULT_QUESTIONS = [
  '現在、利益率が最も高いiPhoneモデルはどれですか？',
  '各店舗の発送・入金スピードを比較してください',
  '総合的に評価の高い買取店舗を教えてください',
]

export default function AIChat() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'こんにちは！NOVA GPTです。iPhone買取に関するご質問にお答えします。今日はあと10回無料でご利用いただけます。',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [remaining, setRemaining] = useState(10)
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 防止页面滚动
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [isOpen])

  const handleSend = async (content: string) => {
    if (!content.trim() || remaining <= 0 || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setRemaining((prev) => prev - 1)
    setIsLoading(true)

    try {
      // 获取当前价格数据用于分析
      const prices = await apiGet<any[]>('/api/v1/prices?limit=1000')
      
      // 调用 AI（这里使用简单的模拟，实际应该调用后端 API）
      const response = await mockAIResponse(content, prices)
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '申し訳ありません。エラーが発生しました。もう一度お試しください。',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const mockAIResponse = async (question: string, prices: any[]): Promise<string> => {
    // 模拟 AI 响应延迟
    await new Promise((resolve) => setTimeout(resolve, 1000))

    const lowerQuestion = question.toLowerCase()

    if (lowerQuestion.includes('利益') || lowerQuestion.includes('収益')) {
      const profits = prices.filter((p) => p.profit > 0).sort((a, b) => b.profit - a.profit)
      const top = profits[0]
      if (top) {
        return `現在、利益率が最も高いのは${top.product.model} ${top.product.capacity}です。${top.store.name}での買取価格は${top.price.toLocaleString()}円で、定価との差は+${top.profit.toLocaleString()}円の利益が見込めます。`
      }
    }

    if (lowerQuestion.includes('発送') || lowerQuestion.includes('入金') || lowerQuestion.includes('スピード')) {
      return '買取BASEと携帯空間が入金スピードで評価が高く、商品到着後1-2営業日での振込が可能です。森森買取も同日入金に対応しており、スピード重視の方におすすめです。'
    }

    if (lowerQuestion.includes('店舗') || lowerQuestion.includes('おすすめ')) {
      return '総合的に評価が高いのは買取BASEと森森買取です。買取価格が高く、入金も迅速です。特にiPhone 17 Pro Maxシリーズでは、買取BASEが最も高価格を提示しています。'
    }

    return 'ご質問ありがとうございます。現在のデータでは、iPhone 17 Pro Maxシリーズが全体的に高価格で買取されています。具体的なモデルについてお知りになりたい場合は、商品名を教えてください。'
  }

  return (
    <>
      {/* 悬浮入口按钮 */}
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-purple-600 text-white px-4 py-2 rounded-full shadow-lg hover:shadow-xl transition-all hover:scale-105"
      >
        <Sparkles className="w-4 h-4" />
        <span className="font-medium text-sm">NOVA GPT</span>
      </button>

      {/* 聊天窗口 */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl h-[80vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden">
            {/* 头部 */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-violet-600 to-purple-600">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">NOVA GPT</h3>
                  <p className="text-xs text-white/80">AI買取アドバイザー</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-white/80 bg-white/20 px-3 py-1 rounded-full">
                  残り {remaining} 回
                </span>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 text-white/80 hover:text-white hover:bg-white/20 rounded-full transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* 消息区域 */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] px-4 py-3 rounded-2xl ${
                      message.role === 'user'
                        ? 'bg-violet-600 text-white rounded-br-md'
                        : 'bg-white border border-slate-200 text-slate-800 rounded-bl-md shadow-sm'
                    }`}
                  >
                    <p className="text-sm leading-relaxed">{message.content}</p>
                    <span
                      className={`text-xs mt-1 block ${
                        message.role === 'user' ? 'text-violet-200' : 'text-slate-400'
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString('ja-JP', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                </div>
              ))}

              {/* 默认问题（首次显示） */}
              {messages.length === 1 && (
                <div className="pt-4">
                  <p className="text-xs text-slate-500 mb-3 text-center">よくある質問</p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    {DEFAULT_QUESTIONS.map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(q)}
                        disabled={remaining <= 0}
                        className="text-xs bg-white border border-slate-200 hover:border-violet-400 hover:text-violet-600 px-3 py-2 rounded-full transition-colors text-slate-600"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-slate-200 px-4 py-3 rounded-2xl rounded-bl-md shadow-sm">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* 输入区域 */}
            <div className="p-4 border-t border-slate-200 bg-white">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value.slice(0, 100))}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend(input)}
                    placeholder={remaining > 0 ? '質問を入力してください（最大100文字）' : '本日の無料回数を使い切りました'}
                    disabled={remaining <= 0 || isLoading}
                    maxLength={100}
                    className="w-full px-4 py-3 pr-16 border border-slate-200 rounded-xl focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-100 disabled:bg-slate-50 disabled:text-slate-400"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                    {input.length}/100
                  </span>
                </div>
                <button
                  onClick={() => handleSend(input)}
                  disabled={!input.trim() || remaining <= 0 || isLoading}
                  className="px-4 py-3 bg-violet-600 text-white rounded-xl hover:bg-violet-700 disabled:bg-slate-200 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
              <p className="text-xs text-slate-400 mt-2 text-center">
                ※刷新すると残り回数がリセットされます
              </p>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
