import type { Language } from '../i18n'

export interface DevelopmentLogEntry {
  period: string
  phase: Record<Language, string>
  title: Record<Language, string>
  content: Record<Language, string>
}

export const DEVELOPMENT_LOGS: DevelopmentLogEntry[] = [
  {
    period: '2025.05',
    phase: { en: 'Foundation', zh: '产品基础', ja: 'プロダクト基盤' },
    title: {
      en: 'Defined the foundation of NOVA AI',
      zh: '确定 NOVA AI 的产品基础',
      ja: 'NOVA AIのプロダクト基盤を設計',
    },
    content: {
      en: 'Defined a clear product structure for organizing smartphone models, stores, prices, and market changes.',
      zh: '围绕手机型号、店铺、价格和市场变化，建立清晰统一的产品结构。',
      ja: '機種、店舗、価格、市場変動を整理し、比較しやすいプロダクト構造を整えました。',
    },
  },
  {
    period: '2025.08',
    phase: { en: 'Interface', zh: '界面设计', ja: 'インターフェース' },
    title: {
      en: 'Built the first price comparison interface',
      zh: '完成首版价格比较界面',
      ja: '価格比較UIの初期版を構築',
    },
    content: {
      en: 'Introduced model grouping, capacity ordering, best-price highlights, store details, and a mobile-friendly layout.',
      zh: '加入机型分组、容量排序、最高价提示、店铺明细和移动端布局。',
      ja: '機種別表示、容量順、最高価格、店舗詳細、モバイル表示をまとめて整備しました。',
    },
  },
  {
    period: '2025.11',
    phase: { en: 'Data Quality', zh: '数据质量', ja: 'データ品質' },
    title: {
      en: 'Improved product and price consistency',
      zh: '提高商品与价格的一致性',
      ja: '商品・価格データの一貫性を改善',
    },
    content: {
      en: 'Unified model, capacity, color, and price notation to make comparisons clearer and more dependable.',
      zh: '统一机型、容量、颜色和价格写法，让比较结果更清楚、更可靠。',
      ja: '機種、容量、カラー、価格の表記を統一し、比較結果の信頼性を高めました。',
    },
  },
  {
    period: '2026.01',
    phase: { en: 'Service', zh: '服务化', ja: 'サービス化' },
    title: {
      en: 'Prepared NOVA AI for stable public use',
      zh: '完成 NOVA AI 的稳定运行基础',
      ja: 'NOVA AIの安定運用基盤を整備',
    },
    content: {
      en: 'Moved from a prototype to a service that can handle large price datasets and continuous product updates.',
      zh: '从原型升级为能够稳定处理大量价格数据和持续产品更新的服务。',
      ja: '試作段階から、大量の価格データと継続的な更新に対応できるサービスへ移行しました。',
    },
  },
  {
    period: '2026.02',
    phase: { en: 'Public Release', zh: '公开发布', ja: '本番公開' },
    title: {
      en: 'Released the live comparison experience',
      zh: '上线实时价格比较体验',
      ja: 'リアルタイム価格比較を公開',
    },
    content: {
      en: 'Connected the main dashboard, price list, store directory, and product pages into one fast browsing flow.',
      zh: '把首页、价格列表、店铺目录和商品页面整合成顺畅快速的浏览流程。',
      ja: 'トップ、価格一覧、店舗一覧、商品詳細をひとつの軽快な閲覧フローにまとめました。',
    },
  },
  {
    period: '2026.03',
    phase: { en: 'Price History', zh: '价格历史', ja: '価格履歴' },
    title: {
      en: 'Added price history and market movement views',
      zh: '加入价格历史与市场变化视图',
      ja: '価格履歴と市場変動表示を追加',
    },
    content: {
      en: 'Added update times, store-by-store prices, daily highs, and charts for understanding market movement.',
      zh: '加入更新时间、店铺价格、每日高价和图表，方便确认市场变化。',
      ja: '更新日時、店舗別価格、日次高値、チャートを追加し、市場変動を確認しやすくしました。',
    },
  },
  {
    period: '2026.04',
    phase: { en: 'AI', zh: 'AI 功能', ja: 'AI機能' },
    title: {
      en: 'Released AI-assisted price guidance',
      zh: '上线 AI 价格咨询',
      ja: 'AIによる価格相談を公開',
    },
    content: {
      en: 'Added natural-language guidance for supported models, store comparisons, selling timing, and multi-device quotes.',
      zh: '支持用自然语言查询机型、店铺比较、出售时机和多台设备合计价格。',
      ja: '機種、店舗比較、売却タイミング、複数台見積もりを自然な言葉で相談できるようにしました。',
    },
  },
  {
    period: '2026.05',
    phase: { en: 'Reliability', zh: '稳定性', ja: '信頼性' },
    title: {
      en: 'Strengthened release and data checks',
      zh: '强化发布与数据检查',
      ja: '公開・データ確認を強化',
    },
    content: {
      en: 'Improved validation, release checks, and error handling to keep public information stable and current.',
      zh: '完善数据验证、发布检查和异常处理，让公开信息保持稳定和及时。',
      ja: 'データ検証、公開前確認、エラー処理を見直し、安定した情報提供を強化しました。',
    },
  },
  {
    period: '2026.06',
    phase: { en: 'Accounts', zh: '会员功能', ja: 'アカウント' },
    title: {
      en: 'Added the member service foundation',
      zh: '加入会员服务基础',
      ja: '会員サービスの基盤を追加',
    },
    content: {
      en: 'Added registration, login, account pages, and the foundation for personalized consultation features.',
      zh: '加入注册、登录、账户页面，并为个性化咨询功能做好基础。',
      ja: '会員登録、ログイン、アカウント画面を追加し、個別相談機能の基盤を整えました。',
    },
  },
  {
    period: '2026.07',
    phase: { en: 'Expansion', zh: '功能扩展', ja: '機能拡張' },
    title: {
      en: 'Expanded stores, products, and mobile usability',
      zh: '扩展店铺、商品与手机端体验',
      ja: '店舗・商品・モバイル体験を拡張',
    },
    content: {
      en: 'Expanded store and product coverage while refining navigation and compact mobile layouts.',
      zh: '增加店铺和商品覆盖，同时优化导航与紧凑的手机端布局。',
      ja: '店舗・商品情報を拡充し、ナビゲーションとモバイル表示を改善しました。',
    },
  },
  {
    period: '2026.08',
    phase: { en: 'API Platform', zh: 'API 技术', ja: 'API基盤' },
    title: {
      en: 'Updated the price analysis API and delivery foundation',
      zh: '更新价格分析 API 与服务基础',
      ja: '価格分析APIの技術更新と提供基盤を整備',
    },
    content: {
      en: 'Added versioned data contracts, market outlier filtering, rate limits, and authentication safeguards for stable price analysis delivery.',
      zh: '加入版本化数据契约、市场异常值过滤、访问限流和认证保护，为稳定提供价格分析功能打好基础。',
      ja: 'バージョン管理されたデータ契約、相場外れ値除外、レート制限、認証保護を追加し、価格分析機能を安定して提供できる基盤を整えました。',
    },
  },
]
