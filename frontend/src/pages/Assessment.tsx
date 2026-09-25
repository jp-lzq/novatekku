import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Check, ClipboardCheck, ExternalLink, Minus, Plus, Route, Trash2 } from 'lucide-react'
import { apiGet, apiPost } from '../lib/api'
import { useI18n, type Language } from '../i18n'
import { LightPage, PageHeader, lightPanelClass } from '../components/PageChrome'

interface Store {
  id: number
  name: string
  website_url?: string | null
}

interface Product {
  id: number
  model: string
  capacity: string
  colors: ColorVariant[]
}

interface ColorVariant {
  variant_id: number
  code: string
  name_ja: string
  name_en: string
  name_zh: string
}

interface AssessmentData {
  products: Product[]
}

interface SelectedItem {
  productId: number
  variantId: number
  quantity: number
}

interface OfferLine {
  product: Product
  color: ColorVariant
  quantity: number
  unitPrice: number
}

interface StoreOffer {
  store: Store
  applicationUrl: string
  total: number
  lines: OfferLine[]
}

interface RouteStop {
  store: Store
  applicationUrl: string
  total: number
  lines: OfferLine[]
}

interface AssessmentQuote {
  store_offers: Array<Omit<StoreOffer, 'applicationUrl'>>
  route_stops: Array<Omit<RouteStop, 'applicationUrl'>>
  route_total: number
}

const APPLICATION_URLS: Record<string, string> = {
  '森森買取': 'https://www.morimori-kaitori.jp/flow/store',
  '買取商店': 'https://www.kaitorishouten-co.jp/shopflow?id=4',
  '買取一丁目': 'https://www.1-chome.com/purchaseInStore',
  '買取ルデヤ': 'https://kaitori-rudeya.com/guide/order/shopcounter',
  '買取ホムラ': 'https://kaitori-homura.com/how-to-sell?tab=store',
  'PANDA買取': 'https://panda-kaitori.co.jp/flow.html',
}

const COPY: Record<Language, {
  title: string
  eyebrow: string
  lead: string
  testBadge: string
  selectPhone: string
  phonePlaceholder: string
  color: string
  colorPlaceholder: string
  quantity: string
  quantityPreset: string
  quantityManual: string
  add: string
  remove: string
  selected: string
  empty: string
  confirm: string
  reset: string
  results: string
  bestRoute: string
  bestRouteLead: string
  oneStore: string
  oneStoreLead: string
  sell: string
  items: string
  noOffers: string
  notice: string
  loading: string
}> = {
  en: {
    title: 'Valuation',
    eyebrow: 'NOVA SELLING ROUTE',
    lead: 'Add phones and quantities to compare total buyback values and selling routes.',
    testBadge: 'TEST',
    selectPhone: 'Add a phone',
    phonePlaceholder: 'Select model and capacity',
    color: 'Color',
    colorPlaceholder: 'Select color',
    quantity: 'Qty',
    quantityPreset: '1–9',
    quantityManual: 'Type',
    add: 'Add',
    remove: 'Remove',
    selected: 'Selected phones',
    empty: 'No phones added yet.',
    confirm: 'Compare totals',
    reset: 'Start over',
    results: 'Valuation result',
    bestRoute: 'Highest-value route',
    bestRouteLead: 'Split the phones between stores to maximize the reference total.',
    oneStore: 'Sell everything to one store',
    oneStoreLead: 'Stores that currently list every selected phone.',
    sell: 'Store buyback guide',
    items: 'phones',
    noOffers: 'No store currently lists every selected phone. Check the split route instead.',
    notice: 'Reference totals use the latest local listed prices. Final value depends on condition and each store’s rules.',
    loading: 'Loading local prices…',
  },
  zh: {
    title: '査定',
    eyebrow: 'NOVA 卖出路线',
    lead: '添加手机型号和数量，比较商家总价以及更高价格的卖出路线。',
    testBadge: '测试功能',
    selectPhone: '添加手机',
    phonePlaceholder: '选择型号和容量',
    color: '颜色',
    colorPlaceholder: '选择颜色',
    quantity: '数量',
    quantityPreset: '选择1–9',
    quantityManual: '输入',
    add: '添加',
    remove: '删除',
    selected: '已选择手机',
    empty: '还没有添加手机。',
    confirm: '确认并计算',
    reset: '重新选择',
    results: '査定结果',
    bestRoute: '最高价卖出路线',
    bestRouteLead: '按照当前价格分开卖出，获得更高的参考总价。',
    oneStore: '全部卖给同一家店',
    oneStoreLead: '以下商家目前都有您选择的全部机型。',
    sell: '查看店头收购',
    items: '台',
    noOffers: '暂时没有一家商家覆盖全部机型，请参考上面的分开卖出路线。',
    notice: '总价根据最新本地公开价格计算，仅供参考。最终价格以手机状态和商家査定规则为准。',
    loading: '正在读取本地价格…',
  },
  ja: {
    title: '査定',
    eyebrow: 'NOVA 売却ルート',
    lead: '機種と台数を追加して、店舗別の合計金額と高く売れるルートを比較できます。',
    testBadge: 'テスト機能',
    selectPhone: '端末を追加',
    phonePlaceholder: '機種・容量を選択',
    color: 'カラー',
    colorPlaceholder: 'カラーを選択',
    quantity: '台数',
    quantityPreset: '1～9から選択',
    quantityManual: '直接入力',
    add: '追加',
    remove: '削除',
    selected: '選択した端末',
    empty: '端末がまだ追加されていません。',
    confirm: '合計を比較',
    reset: '選び直す',
    results: '査定結果',
    bestRoute: '最高額の売却ルート',
    bestRouteLead: '現在の価格をもとに店舗を分け、参考合計額を高くします。',
    oneStore: 'すべて同じ店舗へ売る',
    oneStoreLead: '選択した全機種の価格がある店舗です。',
    sell: '店頭買取へ',
    items: '台',
    noOffers: '全機種を扱う店舗が現在ありません。上の分割ルートをご確認ください。',
    notice: '最新のローカル掲載価格による参考額です。端末状態や店舗条件により最終査定額は変わります。',
    loading: 'ローカル価格を読み込み中…',
  },
}

function formatPrice(value: number) {
  return `¥${value.toLocaleString('ja-JP')}`
}

function colorLabel(color: ColorVariant, language: Language) {
  if (language === 'zh') return color.name_zh
  if (language === 'en') return color.name_en
  return color.name_ja
}

function productLabel(product: Product, color?: ColorVariant, language: Language = 'ja') {
  const capacity = /^\d+$/.test(product.capacity) ? `${product.capacity}GB` : product.capacity
  return `${product.model} · ${capacity}${color ? ` · ${colorLabel(color, language)}` : ''}`
}

function sortProducts(a: Product, b: Product) {
  return b.model.localeCompare(a.model, 'en', { numeric: true }) || a.capacity.localeCompare(b.capacity, 'en', { numeric: true })
}

export default function Assessment() {
  const { language } = useI18n()
  const copy = COPY[language]
  const [productId, setProductId] = useState<number | ''>('')
  const [variantId, setVariantId] = useState<number | ''>('')
  const [addQuantity, setAddQuantity] = useState(1)
  const [selectedItems, setSelectedItems] = useState<SelectedItem[]>([])
  const [confirmed, setConfirmed] = useState(false)
  const [quote, setQuote] = useState<AssessmentQuote | null>(null)
  const [quoteLoading, setQuoteLoading] = useState(false)

  const { data, isLoading } = useQuery<AssessmentData>({
    queryKey: ['assessment-prices'],
    queryFn: () => apiGet<AssessmentData>('/api/v1/prices/assessment'),
    staleTime: 1000 * 60 * 5,
    refetchOnWindowFocus: false,
  })

  const products = useMemo(() => {
    return (data?.products ?? [])
      .filter((product) => /^iPhone/i.test(product.model) && product.colors.length > 0)
      .sort(sortProducts)
  }, [data])

  useEffect(() => {
    if (productId === '' && products.length > 0) setProductId(products[0].id)
  }, [productId, products])

  const productById = useMemo(() => new Map(products.map((product) => [product.id, product])), [products])
  const selectedProduct = productId === '' ? undefined : productById.get(productId)
  const variantById = useMemo(() => new Map(products.flatMap((product) => (
    product.colors.map((color) => [color.variant_id, { product, color }] as const)
  ))), [products])

  useEffect(() => {
    if (!selectedProduct) {
      setVariantId('')
      return
    }
    if (!selectedProduct.colors.some((color) => color.variant_id === variantId)) {
      setVariantId(selectedProduct.colors[0]?.variant_id ?? '')
    }
  }, [selectedProduct, variantId])

  const addItem = () => {
    if (productId === '' || variantId === '') return
    setSelectedItems((items) => {
      const existing = items.find((item) => item.variantId === variantId)
      if (existing) {
        return items.map((item) => item.variantId === variantId
          ? { ...item, quantity: Math.min(99, item.quantity + addQuantity) }
          : item)
      }
      return [...items, { productId, variantId, quantity: addQuantity }]
    })
    setAddQuantity(1)
    setConfirmed(false)
    setQuote(null)
  }

  const changeQuantity = (selectedVariantId: number, amount: number) => {
    setSelectedItems((items) => items.map((item) => item.variantId === selectedVariantId
      ? { ...item, quantity: Math.max(1, Math.min(99, item.quantity + amount)) }
      : item))
    setConfirmed(false)
    setQuote(null)
  }

  const removeItem = (selectedVariantId: number) => {
    setSelectedItems((items) => items.filter((item) => item.variantId !== selectedVariantId))
    setConfirmed(false)
    setQuote(null)
  }

  const storeOffers = useMemo<StoreOffer[]>(() => (quote?.store_offers ?? []).map((offer) => ({
    ...offer,
    applicationUrl: APPLICATION_URLS[offer.store.name] || offer.store.website_url || '#',
  })), [quote])
  const routeStops = useMemo<RouteStop[]>(() => (quote?.route_stops ?? []).map((stop) => ({
    ...stop,
    applicationUrl: APPLICATION_URLS[stop.store.name] || stop.store.website_url || '#',
  })), [quote])
  const routeTotal = quote?.route_total ?? 0

  const confirmAssessment = async () => {
    if (selectedItems.length === 0 || quoteLoading) return
    setQuoteLoading(true)
    setConfirmed(false)
    try {
      const nextQuote = await apiPost<AssessmentQuote>('/api/v1/prices/assessment', {
        items: selectedItems.map((item) => ({ variant_id: item.variantId, quantity: item.quantity })),
      })
      setQuote(nextQuote)
      setConfirmed(true)
    } finally {
      setQuoteLoading(false)
    }
  }

  const selectedCount = selectedItems.reduce((sum, item) => sum + item.quantity, 0)

  return (
    <LightPage>
      <PageHeader title={copy.title} />
      <main className="mx-auto max-w-5xl px-3 py-4 sm:px-4 sm:py-10">
        <section className={`overflow-hidden border-t-2 border-t-violet-500 p-5 sm:p-8 ${lightPanelClass}`}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold tracking-[0.2em] text-violet-600">{copy.eyebrow}</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">{copy.title}</h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">{copy.lead}</p>
            </div>
            <span className="shrink-0 rounded-full bg-violet-50 px-3 py-1 text-[10px] font-semibold text-violet-700">{copy.testBadge}</span>
          </div>

          <div className="mt-8 rounded-2xl border border-slate-200 bg-[#f8f9fc] p-4 sm:p-5">
            <h2 className="text-base font-semibold text-slate-950">{copy.selectPhone}</h2>
            {isLoading ? (
              <p className="mt-4 text-sm text-slate-500">{copy.loading}</p>
            ) : (
              <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1.25fr)_minmax(140px,0.8fr)_minmax(170px,0.7fr)_96px]">
                <select
                  value={productId}
                  onChange={(event) => {
                    setProductId(Number(event.target.value))
                    setVariantId('')
                  }}
                  className="min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-900 outline-none focus:border-violet-400"
                >
                  <option value="">{copy.phonePlaceholder}</option>
                  {products.map((product) => <option key={product.id} value={product.id}>{productLabel(product)}</option>)}
                </select>
                <select
                  value={variantId}
                  onChange={(event) => setVariantId(Number(event.target.value))}
                  aria-label={copy.color}
                  className="min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm text-slate-900 outline-none focus:border-violet-400"
                >
                  <option value="">{copy.colorPlaceholder}</option>
                  {selectedProduct?.colors.map((color) => (
                    <option key={color.variant_id} value={color.variant_id}>{colorLabel(color, language)}</option>
                  ))}
                </select>
                <div className="grid grid-cols-[72px_minmax(0,1fr)] overflow-hidden rounded-xl border border-slate-200 bg-white">
                  <select
                    value={addQuantity >= 1 && addQuantity <= 9 ? addQuantity : ''}
                    onChange={(event) => {
                      if (event.target.value) setAddQuantity(Number(event.target.value))
                    }}
                    aria-label={copy.quantityPreset}
                    className="min-w-0 border-r border-slate-200 bg-slate-50 px-2 py-3 text-center text-sm font-semibold text-slate-900 outline-none focus:bg-violet-50"
                  >
                    <option value="">1–9</option>
                    {Array.from({ length: 9 }, (_, index) => index + 1).map((quantity) => (
                      <option key={quantity} value={quantity}>{quantity}</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={addQuantity}
                    onChange={(event) => {
                      const digits = event.target.value.replace(/\D/g, '').slice(0, 2)
                      setAddQuantity(Math.max(1, Math.min(99, Number(digits) || 1)))
                    }}
                    aria-label={`${copy.quantity}・${copy.quantityManual}`}
                    className="min-w-0 w-full bg-transparent px-3 py-3 text-center text-sm font-semibold text-slate-900 outline-none"
                  />
                </div>
                <button
                  type="button"
                  onClick={addItem}
                  disabled={productId === '' || variantId === ''}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white hover:bg-violet-700 disabled:bg-slate-300"
                >
                  <Plus className="h-4 w-4" />
                  {copy.add}
                </button>
              </div>
            )}
          </div>

          <div className="mt-6">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-base font-semibold text-slate-950">{copy.selected}</h2>
              {selectedCount > 0 && <span className="text-xs font-medium text-slate-500">{selectedCount}{copy.items}</span>}
            </div>
            {selectedItems.length === 0 ? (
              <div className="mt-3 rounded-xl border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">{copy.empty}</div>
            ) : (
              <div className="mt-3 grid gap-2">
                {selectedItems.map((item) => {
                  const selectedVariant = variantById.get(item.variantId)
                  if (!selectedVariant) return null
                  const { product, color } = selectedVariant
                  return (
                    <div key={item.variantId} className="grid grid-cols-[40px_minmax(0,1fr)_40px] items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 sm:grid-cols-[40px_minmax(0,1fr)_auto_40px]">
                      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-50 text-lg">📱</div>
                      <p className="min-w-0 truncate text-sm font-semibold text-slate-900">{productLabel(product, color, language)}</p>
                      <button type="button" onClick={() => removeItem(item.variantId)} className="col-start-3 row-start-1 grid h-10 w-10 shrink-0 place-items-center rounded-full text-slate-400 hover:bg-rose-50 hover:text-rose-600 sm:col-start-4" aria-label={`${copy.remove} ${productLabel(product, color, language)}`}>
                        <Trash2 className="h-4 w-4" />
                      </button>
                      <div className="col-span-2 col-start-2 row-start-2 flex w-fit shrink-0 items-center rounded-full border border-slate-200 bg-slate-50 sm:col-span-1 sm:col-start-3 sm:row-start-1">
                        <button type="button" onClick={() => changeQuantity(item.variantId, -1)} className="grid h-9 w-9 place-items-center text-slate-500" aria-label="-1">
                          <Minus className="h-3.5 w-3.5" />
                        </button>
                        <span className="w-7 text-center text-sm font-semibold text-slate-900">{item.quantity}</span>
                        <button type="button" onClick={() => changeQuantity(item.variantId, 1)} className="grid h-9 w-9 place-items-center text-slate-500" aria-label="+1">
                          <Plus className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <div className="mt-6 flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={confirmAssessment}
              disabled={selectedItems.length === 0 || quoteLoading}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-violet-700 px-5 py-3.5 text-sm font-semibold text-white hover:bg-violet-800 disabled:bg-slate-300"
            >
              <ClipboardCheck className="h-4 w-4" />
              {quoteLoading ? copy.loading : copy.confirm}
            </button>
            {selectedItems.length > 0 && (
              <button type="button" onClick={() => { setSelectedItems([]); setQuote(null); setConfirmed(false) }} className="rounded-xl border border-slate-200 bg-white px-5 py-3.5 text-sm font-medium text-slate-600 hover:text-slate-950">
                {copy.reset}
              </button>
            )}
          </div>
        </section>

        {confirmed && (
          <section className="mt-5 space-y-5" aria-live="polite">
            <div className="flex items-center gap-3 px-1">
              <span className="grid h-10 w-10 place-items-center rounded-xl bg-slate-950 text-white"><Check className="h-5 w-5" /></span>
              <h2 className="text-xl font-semibold text-slate-950">{copy.results}</h2>
            </div>

            {routeStops.length > 0 && (
              <article className="overflow-hidden rounded-2xl bg-slate-950 p-5 text-white shadow-xl shadow-slate-200 sm:p-7">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-semibold tracking-[0.16em] text-violet-300">BEST ROUTE</p>
                    <h3 className="mt-2 text-xl font-semibold">{copy.bestRoute}</h3>
                    <p className="mt-2 text-sm leading-6 text-white/55">{copy.bestRouteLead}</p>
                  </div>
                  <Route className="h-6 w-6 shrink-0 text-violet-300" />
                </div>
                <p className="mt-6 text-4xl font-semibold tracking-tight">{formatPrice(routeTotal)}</p>
                <div className="mt-6 grid gap-3">
                  {routeStops.map((stop, index) => (
                    <div key={stop.store.id} className="rounded-xl border border-white/10 bg-white/[0.06] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="min-w-0 truncate text-sm font-semibold">{index + 1}. {stop.store.name}</p>
                        <p className="shrink-0 font-semibold text-violet-200">{formatPrice(stop.total)}</p>
                      </div>
                      <p className="mt-2 text-xs leading-6 text-white/50">{stop.lines.map((line) => `${productLabel(line.product, line.color, language)} × ${line.quantity}`).join(' / ')}</p>
                      <a href={stop.applicationUrl} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-xs font-semibold text-slate-950">
                        {copy.sell}<ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  ))}
                </div>
              </article>
            )}

            <div>
              <div className="px-1">
                <h3 className="text-lg font-semibold text-slate-950">{copy.oneStore}</h3>
                <p className="mt-1 text-sm text-slate-600">{copy.oneStoreLead}</p>
              </div>
              {storeOffers.length === 0 ? (
                <div className={`mt-3 p-5 text-sm leading-7 text-slate-600 ${lightPanelClass}`}>{copy.noOffers}</div>
              ) : (
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {storeOffers.map((offer, index) => (
                    <article key={offer.store.id} className={`p-5 ${lightPanelClass}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-[10px] font-semibold tracking-[0.16em] text-violet-600">OPTION {String(index + 1).padStart(2, '0')}</p>
                          <h4 className="mt-2 truncate text-lg font-semibold text-slate-950">{offer.store.name}</h4>
                        </div>
                        <p className="shrink-0 text-xl font-semibold tracking-tight text-slate-950">{formatPrice(offer.total)}</p>
                      </div>
                      <div className="mt-4 space-y-2 border-t border-slate-100 pt-4">
                        {offer.lines.map((line) => (
                          <div key={line.color.variant_id} className="flex items-center justify-between gap-3 text-xs">
                            <span className="min-w-0 truncate text-slate-500">{productLabel(line.product, line.color, language)} × {line.quantity}</span>
                            <span className="shrink-0 font-medium text-slate-700">{formatPrice(line.unitPrice * line.quantity)}</span>
                          </div>
                        ))}
                      </div>
                      <a href={offer.applicationUrl} target="_blank" rel="noreferrer" className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white hover:bg-violet-700">
                        {copy.sell}<ExternalLink className="h-4 w-4" />
                      </a>
                    </article>
                  ))}
                </div>
              )}
            </div>

            <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-6 text-amber-800">{copy.notice}</p>
          </section>
        )}
      </main>
    </LightPage>
  )
}
