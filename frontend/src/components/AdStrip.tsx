import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CreditCard, Gift, Link2, Smartphone, type LucideIcon } from 'lucide-react'
import { apiGet } from '../lib/api'
import { useI18n, type Language } from '../i18n'

// Copy and links live in the private site_ads data; this file only draws the slot.
interface Ad {
  key: string
  icon: string
  brand: string
  text: Record<Language, string>
  href: string
}

interface AdsResponse {
  slot: string
  ads: Ad[]
}

const ICONS: Record<string, LucideIcon> = { phone: Smartphone, card: CreditCard, gift: Gift, link: Link2 }
const ROTATE_MS = 6000

function AdCard({ ad, language }: { ad: Ad; language: Language }) {
  const Icon = ICONS[ad.icon] ?? Link2
  return (
    <a
      href={ad.href}
      target="_blank"
      rel="noopener noreferrer"
      className="group relative flex min-w-0 flex-1 items-center gap-3 rounded-xl border border-white/70 bg-white/45 px-3.5 py-2.5 backdrop-blur transition-colors hover:border-slate-200 hover:bg-white/80"
    >
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/80 text-slate-400 group-hover:text-slate-600">
        <Icon className="h-4 w-4" />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-[12px] font-medium text-slate-600">{ad.brand}</span>
        <span className="block truncate text-[11px] text-slate-400">{ad.text[language]}</span>
      </span>
      <span className="absolute right-2 top-1.5 text-[9px] font-medium tracking-wide text-slate-300">PR</span>
    </a>
  )
}

/** Quiet sponsored links under the navigation; one rotating card on phones. Renders nothing without ads. */
export default function AdStrip({ slot }: { slot: string }) {
  const { language } = useI18n()
  const [index, setIndex] = useState(0)
  const { data } = useQuery({
    queryKey: ['ads', slot],
    queryFn: () => apiGet<AdsResponse>('/api/v1/ads', { params: { slot } }),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
  const ads = data?.ads ?? []

  useEffect(() => {
    if (ads.length < 2) return
    const timer = window.setInterval(() => setIndex((value) => (value + 1) % ads.length), ROTATE_MS)
    return () => window.clearInterval(timer)
  }, [ads.length])

  if (!ads.length) return null
  return (
    <aside aria-label="PR" className="relative mx-auto w-full max-w-5xl px-4 pt-4 sm:px-6">
      <div className="hidden gap-3 sm:flex">
        {ads.map((ad) => <AdCard key={ad.key} ad={ad} language={language} />)}
      </div>
      <div className="flex sm:hidden">
        <AdCard ad={ads[index % ads.length]} language={language} />
      </div>
    </aside>
  )
}
