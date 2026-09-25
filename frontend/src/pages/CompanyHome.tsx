import { ArrowRight, ArrowUpRight, Database, LineChart, Sparkles } from 'lucide-react'
import { type Language, useI18n } from '../i18n'

type CompanyCopy = {
  brand: string
  eyebrow: string
  title: string
  lead: string
  aiButton: string
  productEyebrow: string
  productTitle: string
  productLead: string
  signalLabel: string
  latestRecordsLabel: string
  historyRecordsLabel: string
  latestRecordsValue: string
  historyRecordsValue: string
  capabilities: Array<{ number: string; title: string; body: string }>
}

const COMPANY_COPY: Record<Language, CompanyCopy> = {
  en: {
    brand: 'NOVATECH',
    eyebrow: 'AI PRODUCT STUDIO · TOKYO',
    title: 'Turn data into confident decisions.',
    lead: 'We turn complex market data into clear, reliable decisions and build AI products designed for real-world use.',
    aiButton: 'Enter AI',
    productEyebrow: 'OUR FIRST PRODUCT',
    productTitle: 'NOVA AI',
    productLead: 'Live iPhone buyback intelligence, powered by local price data and natural conversation.',
    signalLabel: 'LIVE PRICE SIGNAL',
    latestRecordsLabel: 'LATEST DATA RECORDS',
    historyRecordsLabel: 'HISTORICAL DATA RECORDS · 2020–2025',
    latestRecordsValue: '10M+',
    historyRecordsValue: '50M+',
    capabilities: [
      { number: '01', title: 'Price intelligence', body: 'Real market data, filtered and structured for faster decisions.' },
      { number: '02', title: 'Natural conversation', body: 'Ask about smartphones, prices, and the best time to sell.' },
      { number: '03', title: 'Built for movement', body: 'A multilingual product designed for a cross-border market.' },
    ],
  },
  zh: {
    brand: 'NOVATECH',
    eyebrow: 'AI PRODUCT STUDIO · TOKYO',
    title: '让数据，成为可靠的判断。',
    lead: '我们把复杂的市场数据变成清晰、可靠的判断，开发真正能够投入使用的 AI 产品。',
    aiButton: '进入 AI',
    productEyebrow: '首个公开产品',
    productTitle: 'NOVA AI',
    productLead: '结合本地价格数据与自然对话，实时分析 iPhone 回收市场。',
    signalLabel: '实时价格信号',
    latestRecordsLabel: '最新数据记录数',
    historyRecordsLabel: '历史数据记录数 · 2020–2025',
    latestRecordsValue: '1000万+',
    historyRecordsValue: '5000万+',
    capabilities: [
      { number: '01', title: '价格智能', body: '整理真实市场数据、排除异常值，让判断更直接。' },
      { number: '02', title: '自然对话', body: '可以询问手机、价格以及适合出售的时间。' },
      { number: '03', title: '面向流动市场', body: '为跨境市场设计的多语言 AI 产品。' },
    ],
  },
  ja: {
    brand: 'NOVATECH',
    eyebrow: 'AI PRODUCT STUDIO · TOKYO',
    title: 'データを、確かな判断へ。',
    lead: '複雑な市場データを明確で信頼できる判断へ変え、実際に使えるAIプロダクトを開発しています。',
    aiButton: 'AIへ',
    productEyebrow: '最初の公開プロダクト',
    productTitle: 'NOVA AI',
    productLead: 'ローカル価格データと自然な対話を組み合わせた、iPhone買取市場のリアルタイムAIです。',
    signalLabel: 'リアルタイム価格シグナル',
    latestRecordsLabel: '最新データ収録件数',
    historyRecordsLabel: '履歴データ収録件数 · 2020–2025',
    latestRecordsValue: '1,000万+',
    historyRecordsValue: '5,000万+',
    capabilities: [
      { number: '01', title: '価格インテリジェンス', body: '実市場データを整理し、異常値を除外して判断を明確にします。' },
      { number: '02', title: '自然な対話', body: 'スマートフォン、価格、売却タイミングを自然な言葉で相談できます。' },
      { number: '03', title: '動く市場のために', body: '越境市場に向けて設計した、多言語対応のAIプロダクトです。' },
    ],
  },
}

const PRODUCT_URL = 'https://ai.novatekku.com/'

export default function CompanyHome() {
  const { language } = useI18n()
  const copy = COMPANY_COPY[language]
  const capabilityStyles = [
    'border-t-violet-400/70 bg-[#121022]',
    'border-t-cyan-400/70 bg-[#0b161e]',
    'border-t-emerald-400/70 bg-[#0b1714]',
  ]

  return (
    <main className="min-h-screen overflow-hidden bg-[#07080b] text-white">
      <header className="fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-[#07080b] sm:bg-[#07080b]/90 sm:backdrop-blur-md">
        <div className="mx-auto flex h-[72px] max-w-7xl items-center px-4 sm:px-6 lg:px-8">
          <a href="/" className="flex items-center gap-3" aria-label={copy.brand}>
            <span className="grid h-9 w-9 place-items-center rounded-full border border-white/25 text-xs font-semibold tracking-wider">
              N
            </span>
            <span className="hidden text-sm font-semibold tracking-[0.22em] sm:block">{copy.brand}</span>
          </a>
        </div>
      </header>

      <a
        href={PRODUCT_URL}
        className="fixed right-4 top-4 z-[70] inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-full bg-white px-4 text-xs font-semibold text-slate-950 shadow-lg shadow-black/20 transition-transform hover:-translate-y-0.5 sm:px-5 sm:text-sm"
      >
        {copy.aiButton}
        <ArrowUpRight className="h-4 w-4" />
      </a>

      <section className="relative isolate px-4 pb-20 pt-32 sm:px-6 sm:pb-28 sm:pt-40 lg:px-8">
        <div
          className="pointer-events-none absolute inset-0 -z-10"
          style={{
            background:
              'radial-gradient(circle at 50% 0%, rgba(124, 58, 237, 0.34), transparent 40%), radial-gradient(circle at 100% 42%, rgba(6, 182, 212, 0.16), transparent 34%)',
          }}
        />

        <div className="mx-auto max-w-7xl">
          <div className="mx-auto max-w-5xl text-center">
            <p className="text-[11px] font-semibold tracking-[0.28em] text-violet-200/80 sm:text-xs">{copy.eyebrow}</p>
            <h1 className="mx-auto mt-7 max-w-5xl text-4xl font-medium leading-[1.05] tracking-[-0.055em] sm:text-7xl sm:leading-[0.98] lg:text-[96px]">
              {copy.title}
            </h1>
            <p className="mx-auto mt-7 max-w-2xl text-base leading-8 text-white/75 sm:text-lg">{copy.lead}</p>
            <a
              href={PRODUCT_URL}
              className="mt-9 inline-flex items-center gap-3 rounded-full border border-white/20 bg-white/10 px-6 py-3 text-sm font-semibold transition-colors hover:bg-white hover:text-slate-950"
            >
              {copy.productTitle}
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>

          <div className="relative mx-auto mt-16 max-w-6xl sm:mt-24">
            <div className="relative overflow-hidden rounded-[28px] border border-violet-300/25 bg-[#141827] p-2 sm:rounded-[38px] sm:p-3 sm:shadow-2xl sm:shadow-black/50">
              <div className="overflow-hidden rounded-[22px] border border-white/15 bg-[#090c12] sm:rounded-[30px]">
                <div className="flex h-12 items-center border-b border-white/10 px-4 sm:px-6">
                  <div className="flex gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-white/15" />
                    <span className="h-2 w-2 rounded-full bg-white/15" />
                    <span className="h-2 w-2 rounded-full bg-white/15" />
                  </div>
                  <span className="mx-auto text-[10px] font-medium tracking-[0.24em] text-white/35">NOVA INTELLIGENCE</span>
                </div>

                <div className="grid min-h-[420px] lg:grid-cols-[1.35fr_0.65fr]">
                  <div className="relative flex min-h-[360px] flex-col justify-between overflow-hidden border-b border-white/15 bg-gradient-to-br from-[#17142d] via-[#0d1320] to-[#07171a] p-6 sm:p-10 lg:border-b-0 lg:border-r">
                    <div className="absolute right-[-5rem] top-[-7rem] h-80 w-80 rounded-full border border-cyan-300/20 bg-[radial-gradient(circle_at_35%_35%,rgba(255,255,255,0.35),rgba(104,76,255,0.24)_28%,rgba(25,211,255,0.08)_58%,transparent_70%)] shadow-[inset_0_0_70px_rgba(255,255,255,0.08)]" />
                    <div className="relative">
                      <p className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.24em] text-cyan-200/90">
                        <Sparkles className="h-3.5 w-3.5" />
                        {copy.productEyebrow}
                      </p>
                      <h2 className="mt-5 text-5xl font-medium tracking-[-0.05em] sm:text-7xl">{copy.productTitle}</h2>
                      <p className="mt-5 max-w-xl text-sm leading-7 text-white/70 sm:text-base">{copy.productLead}</p>
                    </div>

                    <div className="relative mt-14 flex items-end justify-between gap-5">
                      <div>
                        <p className="text-[10px] tracking-[0.24em] text-white/55">{copy.signalLabel}</p>
                        <div className="mt-3 flex h-12 items-end gap-1">
                          {[18, 31, 25, 42, 36, 56, 48, 72, 61, 84, 76, 96].map((height, index) => (
                            <span
                              key={`${height}-${index}`}
                              className="w-1.5 rounded-full bg-gradient-to-t from-violet-600 to-cyan-300 sm:w-2"
                              style={{ height: `${height}%` }}
                            />
                          ))}
                        </div>
                      </div>
                      <LineChart className="h-8 w-8 text-white/20 sm:h-10 sm:w-10" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-1">
                    <div className="flex flex-col justify-between border-r border-white/15 bg-violet-500/[0.10] p-5 sm:p-7 lg:border-b lg:border-r-0">
                      <Database className="h-5 w-5 text-violet-200" />
                      <div className="mt-14">
                        <p className="text-3xl font-medium tracking-tight sm:text-4xl">{copy.latestRecordsValue}</p>
                        <p className="mt-2 text-[10px] leading-4 tracking-[0.18em] text-white/55">{copy.latestRecordsLabel}</p>
                      </div>
                    </div>
                    <div className="flex flex-col justify-between bg-cyan-400/[0.08] p-5 sm:p-7">
                      <span className="h-2 w-2 rounded-full bg-emerald-400" />
                      <div className="mt-14">
                        <p className="text-3xl font-medium tracking-tight sm:text-4xl">{copy.historyRecordsValue}</p>
                        <p className="mt-2 text-[10px] leading-4 tracking-[0.18em] text-white/55">{copy.historyRecordsLabel}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-white/15 bg-[#090c12] px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
        <div className="mx-auto grid max-w-7xl gap-3 md:grid-cols-3">
          {copy.capabilities.map((item, index) => (
            <article key={item.number} className={`min-h-64 rounded-2xl border border-white/10 border-t-2 p-7 sm:p-9 ${capabilityStyles[index]}`}>
              <p className="text-xs tracking-[0.2em] text-white/50">{item.number}</p>
              <h2 className="mt-16 text-2xl font-medium tracking-tight">{item.title}</h2>
              <p className="mt-4 max-w-sm text-sm leading-7 text-white/70">{item.body}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}
