import { useLocation } from 'react-router-dom'
import { useI18n, type Language } from '../i18n'
import { LightPage, PageHeader, lightPanelClass } from '../components/PageChrome'

type LegalContent = {
  title: string
  lead: string
  sections: Array<{
    heading: string
    body: string[]
    details?: Array<{ label: string; value: string }>
    links?: Array<{ label: string; href: string }>
  }>
}

const LEGAL_CONTENT: Record<Language, Record<string, LegalContent>> = {
  en: {
    '/company': {
      title: 'Company Overview',
      lead: '',
      sections: [
        {
          heading: 'Company Profile',
          body: [
            'Novatech Co., Ltd. is a Tokyo-based AI company that transforms large, complex market datasets into clear and dependable information for real decisions.',
            'With data quality, speed, and usability at the center, we develop and operate practical products beginning with NOVA AI.',
          ],
        },
        {
          heading: 'Basic Information',
          body: [],
          details: [
            { label: 'Company', value: 'Novatech Co., Ltd.' },
            { label: 'Head Office', value: 'Musashino Building, 2-13-10 Shinjuku, Shinjuku-ku, Tokyo' },
            { label: 'Business', value: 'Planning, development, and operation of data and AI products' },
            { label: 'Corporate No.', value: '0111-01-110714' },
            { label: 'Capital', value: 'JPY 6,000,000' },
            { label: 'Established', value: 'February 17, 2025' },
          ],
        },
        {
          heading: 'Contact',
          body: [],
          links: [
            { label: 'info@novatekku.com', href: 'mailto:info@novatekku.com' },
          ],
        },
        {
          heading: 'Open Source',
          body: [
            "We publish part of NOVA AI's source code on GitHub to share knowledge and contribute to technical progress.",
            'Code reviews, improvement suggestions, and technical questions are welcome.',
          ],
          links: [
            { label: 'GitHub', href: 'https://github.com/jp-lzq/novatekku' },
          ],
        },
      ],
    },
    '/notice': {
      title: 'Notice',
      lead: 'Please review the following points before using NOVA.',
      sections: [
        {
          heading: 'Service Scope',
          body: [
            'NOVA provides publicly collected iPhone buyback price comparisons and AI-assisted guidance for reference.',
            'Prices, supported models, and shop information may change without notice.',
          ],
        },
        {
          heading: 'Pricing Disclaimer',
          body: [
            'Displayed prices are not final assessment guarantees.',
            'Actual quotes may change based on device condition, accessories, network status, and store-side checks.',
          ],
        },
      ],
    },
    '/privacy': {
      title: 'Privacy Policy',
      lead: 'This page outlines how NOVA handles basic usage information.',
      sections: [
        {
          heading: 'Collected Information',
          body: [
            'For member services, NOVA records usernames, email addresses, registration and login times, IP addresses, and browser information.',
            'For the AI feature, NOVA records language settings, questions and answers, protected session identifiers, IP addresses, and browser information.',
          ],
        },
        {
          heading: 'Use of Information',
          body: [
            'We use collected information only for operating the comparison and AI services, account security, usage management, product improvement, and responding to inquiries when necessary.',
            'We do not sell personal information to third parties.',
          ],
        },
      ],
    },
    '/terms': {
      title: 'Terms of Use',
      lead: 'By using NOVA, you agree to the following basic terms.',
      sections: [
        {
          heading: 'Permitted Use',
          body: [
            'Use the service in accordance with applicable laws and do not interfere with normal operation.',
            'Automated abuse, unauthorized copying, and harmful use are prohibited.',
          ],
        },
        {
          heading: 'Limitation',
          body: [
            'NOVA provides information on an as-is basis and does not guarantee completeness or suitability for a specific sale.',
            'Final selling decisions should be made after confirming the latest terms directly with each store.',
          ],
        },
      ],
    },
  },
  zh: {
    '/company': {
      title: '会社概要',
      lead: '',
      sections: [
        {
          heading: '公司简介',
          body: [
            '诺瓦科技株式会社是一家位于东京的 AI 公司。我们把庞大、复杂的市场数据整理成清晰可靠的信息，让判断更简单。',
            '我们重视数据质量、速度和实际使用体验，并以 NOVA AI 为起点，持续开发真正能够投入使用的产品。',
          ],
        },
        {
          heading: '基本信息',
          body: [],
          details: [
            { label: '公司名称', value: '诺瓦科技株式会社' },
            { label: '公司所在地', value: '东京都新宿区新宿2丁目13番10号 武藏野大楼' },
            { label: '业务内容', value: '数据与 AI 产品的策划、开发及运营' },
            { label: '法人编号', value: '0111-01-110714' },
            { label: '注册资本', value: '600万日元' },
            { label: '成立日期', value: '2025年2月17日' },
          ],
        },
        {
          heading: '联系我们',
          body: [],
          links: [
            { label: 'info@novatekku.com', href: 'mailto:info@novatekku.com' },
          ],
        },
        {
          heading: '开源与交流',
          body: [
            '我们在 GitHub 公开 NOVA AI 的部分源代码，希望通过技术共享推动行业进步。',
            '欢迎检查代码、提出改进建议和技术问题。',
          ],
          links: [
            { label: 'GitHub', href: 'https://github.com/jp-lzq/novatekku' },
          ],
        },
      ],
    },
    '/notice': {
      title: '注意事项',
      lead: '使用 NOVA 前，请先确认以下说明。',
      sections: [
        {
          heading: '服务范围',
          body: [
            'NOVA 提供公开收集的 iPhone 回收价格对比，以及 AI 辅助参考建议。',
            '价格、支持机型和店铺信息可能会在未通知的情况下变更。',
          ],
        },
        {
          heading: '价格说明',
          body: [
            '页面显示的价格并不代表最终成交价或最终査定结果。',
            '实际回收价可能会因机器状态、配件、网络限制或店铺审核标准而变化。',
          ],
        },
      ],
    },
    '/privacy': {
      title: '隐私政策',
      lead: '本页说明 NOVA 对基础使用信息的处理方式。',
      sections: [
        {
          heading: '收集的信息',
          body: [
            '会员服务会记录用户名、邮箱、注册及登录时间、IP 地址和浏览器信息。',
            'AI 功能会记录语言设置、问题与回答、经过保护的会话标识、IP 地址和浏览器信息。',
          ],
        },
        {
          heading: '信息用途',
          body: [
            '收集的信息仅用于运营比价与 AI 服务、账户安全、使用次数管理、产品改善，以及在必要时处理咨询。',
            '我们不会将个人信息出售给第三方。',
          ],
        },
      ],
    },
    '/terms': {
      title: '使用条款',
      lead: '使用 NOVA 即视为同意以下基础条款。',
      sections: [
        {
          heading: '允许的使用方式',
          body: [
            '请在遵守适用法律的前提下使用本服务，不得干扰正常运营。',
            '禁止恶意自动化抓取、未授权复制或其他有害使用行为。',
          ],
        },
        {
          heading: '责任限制',
          body: [
            'NOVA 以现状提供信息，不保证其完整性，也不保证一定适用于某次具体卖出。',
            '最终出售前，请务必以各店铺的最新规则与报价为准。',
          ],
        },
      ],
    },
  },
  ja: {
    '/company': {
      title: '会社概要',
      lead: '',
      sections: [
        {
          heading: '会社概要',
          body: [
            'ノーヴァテック株式会社は、東京を拠点に、大規模で複雑な市場データを明確で信頼できる情報へ変えるAI企業です。',
            'データ品質、速度、使いやすさを重視し、NOVA AIをはじめ、実際の判断に使えるプロダクトを開発・運営しています。',
          ],
        },
        {
          heading: '基本情報',
          body: [],
          details: [
            { label: '会社名', value: 'ノーヴァテック株式会社' },
            { label: '所在地', value: '東京都新宿区新宿2丁目13番10号 武蔵野ビル' },
            { label: '事業内容', value: 'データ・AIプロダクトの企画、開発、運営' },
            { label: '会社法人等番号', value: '0111-01-110714' },
            { label: '資本金', value: '600万円' },
            { label: '設立', value: '2025年2月17日' },
          ],
        },
        {
          heading: 'お問い合わせ',
          body: [],
          links: [
            { label: 'info@novatekku.com', href: 'mailto:info@novatekku.com' },
          ],
        },
        {
          heading: 'オープンソース',
          body: [
            'NOVA AIの一部ソースコードをGitHubで公開し、技術の共有と発展に貢献しています。',
            'コードの確認、改善提案、技術的なご質問を歓迎しています。',
          ],
          links: [
            { label: 'GitHub', href: 'https://github.com/jp-lzq/novatekku' },
          ],
        },
      ],
    },
    '/notice': {
      title: '注意事項',
      lead: 'NOVAをご利用いただく前に、以下の点をご確認ください。',
      sections: [
        {
          heading: 'サービス内容について',
          body: [
            'NOVAは、公開されているiPhone買取価格の比較情報と、AIによる参考案内を提供するサービスです。',
            '掲載価格、対応機種、店舗情報は予告なく更新または変更される場合があります。',
          ],
        },
        {
          heading: '価格表示について',
          body: [
            '表示価格は最終査定額を保証するものではありません。',
            '端末の状態、付属品の有無、利用制限、店舗ごとの査定基準によって実際の買取額は変動します。',
          ],
        },
      ],
    },
    '/privacy': {
      title: 'プライバシーポリシー',
      lead: 'NOVAにおける基本的な情報の取り扱いについてご案内します。',
      sections: [
        {
          heading: '取得する情報',
          body: [
            '会員機能では、ユーザー名、メールアドレス、登録・ログイン日時、IPアドレス、ブラウザ情報を記録します。',
            'AI機能では、言語設定、質問と回答、保護されたセッション識別子、IPアドレス、ブラウザ情報を記録します。',
          ],
        },
        {
          heading: '利用目的',
          body: [
            '取得した情報は、価格比較・AIサービスの提供、アカウント保護、利用回数管理、機能改善、お問い合わせ対応のために利用します。',
            '個人情報を第三者へ販売することはありません。',
          ],
        },
      ],
    },
    '/terms': {
      title: '利用規約',
      lead: 'NOVAをご利用いただくことで、以下の基本条件に同意したものとみなします。',
      sections: [
        {
          heading: '利用上のルール',
          body: [
            '法令および公序良俗に反する目的での利用、通常運営を妨げる行為は禁止します。',
            '過度な自動アクセス、無断転載、その他サービスに不利益を与える行為はお控えください。',
          ],
        },
        {
          heading: '免責事項',
          body: [
            'NOVAは情報を現状有姿で提供しており、内容の完全性や特定目的への適合性を保証するものではありません。',
            '最終的な売却判断は、各店舗の最新条件や査定結果をご確認のうえで行ってください。',
          ],
        },
      ],
    },
  },
}

export default function LegalPage() {
  const { language } = useI18n()
  const location = useLocation()
  const content = LEGAL_CONTENT[language][location.pathname] ?? LEGAL_CONTENT.ja['/notice']
  const isCompanySite = import.meta.env.VITE_SITE_MODE === 'company'

  if (isCompanySite) {
    return (
      <div className="min-h-[100dvh] bg-[#07080b] text-white">
        <PageHeader title={content.title} tone="dark" />
        <main className="relative overflow-hidden px-4 pb-20 pt-12 sm:px-6 sm:pb-28 sm:pt-20 lg:px-8">
          <div
            className="pointer-events-none absolute inset-x-0 top-0 h-80"
            style={{ background: 'radial-gradient(circle at 50% 0%, rgba(124, 58, 237, 0.18), transparent 68%)' }}
          />
          <div className="relative mx-auto max-w-6xl">
            <p className="text-[11px] font-semibold tracking-[0.26em] text-violet-300/65">NOVATECH · TOKYO</p>
            <h2 className="mt-5 max-w-4xl text-4xl font-medium tracking-[-0.04em] sm:text-6xl">{content.title}</h2>
            {content.lead && <p className="mt-6 max-w-2xl text-sm leading-8 text-white/55 sm:text-base">{content.lead}</p>}

            <div className="mt-12 grid gap-4 sm:mt-16 md:grid-cols-2">
              {content.sections.map((section, index) => (
                <section
                  key={section.heading}
                  className={`rounded-2xl border border-white/10 border-t-2 p-6 sm:p-8 ${
                    index % 3 === 0
                      ? 'border-t-violet-400/70 bg-[#121022]'
                      : index % 3 === 1
                        ? 'border-t-cyan-400/70 bg-[#0b161e]'
                        : 'border-t-emerald-400/70 bg-[#0b1714]'
                  } ${content.sections.length % 2 === 1 && index === 0 ? 'md:col-span-2' : ''}`}
                >
                  <p className="text-[10px] font-semibold tracking-[0.2em] text-white/35">
                    {String(index + 1).padStart(2, '0')}
                  </p>
                  <h3 className="mt-5 text-xl font-medium tracking-tight text-white">{section.heading}</h3>
                  <div className="mt-4 space-y-3">
                    {section.body.map((paragraph) => (
                      <p key={paragraph} className="text-sm leading-7 text-white/60">
                        {paragraph}
                      </p>
                    ))}
                    {section.details && (
                      <dl className="overflow-hidden rounded-xl border border-white/10 bg-black/10">
                        {section.details.map((detail, detailIndex) => (
                          <div
                            key={detail.label}
                            className={`grid grid-cols-[104px_minmax(0,1fr)] gap-3 px-3.5 py-3.5 sm:grid-cols-[150px_minmax(0,1fr)] sm:px-4 ${
                              detailIndex > 0 ? 'border-t border-white/10' : ''
                            }`}
                          >
                            <dt className="text-[10px] font-semibold leading-6 tracking-[0.1em] text-cyan-200/55">{detail.label}</dt>
                            <dd className="min-w-0 break-words text-sm leading-6 text-white/75">{detail.value}</dd>
                          </div>
                        ))}
                      </dl>
                    )}
                    {section.links?.map((link) => (
                      <a
                        key={link.href}
                        href={link.href}
                        target={link.href.startsWith('http') ? '_blank' : undefined}
                        rel={link.href.startsWith('http') ? 'noreferrer' : undefined}
                        className="block w-fit text-sm font-medium text-white/80 underline decoration-white/25 underline-offset-4 transition-colors hover:text-white"
                      >
                        {link.label}
                      </a>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </div>
        </main>
      </div>
    )
  }

  return (
    <LightPage>
      <PageHeader title={content.title} />

      <main className="mx-auto max-w-5xl px-3 py-4 sm:px-4 sm:py-10">
        <section className={`overflow-hidden p-5 sm:p-9 ${lightPanelClass}`}>
          <div className="mb-8 border-b border-slate-100 pb-7">
            <p className="text-[11px] font-semibold tracking-[0.2em] text-violet-600">NOVA INFORMATION</p>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">{content.title}</h2>
          </div>
          {content.lead && <p className="text-sm leading-7 text-slate-600">{content.lead}</p>}
          <div className={`${content.lead ? 'mt-8' : ''} grid gap-4 md:grid-cols-2`}>
            {content.sections.map((section, index) => (
              <section key={section.heading} className={`rounded-xl border border-slate-200 border-t-2 p-5 ${index % 2 === 0 ? 'border-t-violet-500 bg-violet-50/35' : 'border-t-cyan-500 bg-cyan-50/35'}`}>
                <h3 className="text-base font-semibold text-slate-900">{section.heading}</h3>
                <div className="mt-3 space-y-3">
                  {section.body.map((paragraph) => (
                    <p key={paragraph} className="text-sm leading-7 text-slate-600">
                      {paragraph}
                    </p>
                  ))}
                  {section.details && (
                    <dl className="overflow-hidden rounded-lg border border-slate-200 bg-white/75">
                      {section.details.map((detail, detailIndex) => (
                        <div
                          key={detail.label}
                          className={`grid grid-cols-[104px_minmax(0,1fr)] gap-3 px-3.5 py-3 sm:grid-cols-[145px_minmax(0,1fr)] sm:px-4 ${
                            detailIndex > 0 ? 'border-t border-slate-200' : ''
                          }`}
                        >
                          <dt className="text-[10px] font-semibold leading-6 tracking-[0.08em] text-slate-400">{detail.label}</dt>
                          <dd className="min-w-0 break-words text-sm leading-6 text-slate-700">{detail.value}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                  {section.links?.map((link) => (
                    <a
                      key={link.href}
                      href={link.href}
                      target={link.href.startsWith('http') ? '_blank' : undefined}
                      rel={link.href.startsWith('http') ? 'noreferrer' : undefined}
                      className="block w-fit text-sm font-medium text-violet-700 underline decoration-violet-200 underline-offset-4 transition-colors hover:text-violet-950"
                    >
                      {link.label}
                    </a>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </section>
      </main>
    </LightPage>
  )
}
