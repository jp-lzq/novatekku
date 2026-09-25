import { useQuery } from '@tanstack/react-query'
import { ClipboardCheck, LogIn, Store, Tags, UserPlus } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useI18n, type Language } from '../i18n'
import { getCurrentMember } from '../lib/member'
import { getMemberAuthStatus, memberAuthStatusQueryKey } from '../lib/memberAuth'

const COPY: Record<Language, {
  assessment: string
  prices: string
  stores: string
  login: string
  register: string
}> = {
  ja: { assessment: '査定', prices: '価格', stores: '店舗', login: 'ログイン', register: '会員登録' },
  zh: { assessment: '査定', prices: '价格', stores: '店铺', login: '登录', register: '注册' },
  en: { assessment: 'Valuation', prices: 'Prices', stores: 'Stores', login: 'Log in', register: 'Sign up' },
}

export default function ProductNav() {
  const { language, setLanguage, t } = useI18n()
  const { pathname } = useLocation()
  const copy = COPY[language]
  const member = useQuery({
    queryKey: ['current-member'],
    queryFn: getCurrentMember,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
  const authStatus = useQuery({
    queryKey: memberAuthStatusQueryKey,
    queryFn: getMemberAuthStatus,
    staleTime: 15_000,
    retry: false,
  })

  const navClass = (path: string, featured = false) => {
    const active = pathname === path
    if (featured) {
      return `inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-full px-4 text-sm font-semibold transition-colors ${
        active ? 'bg-violet-700 text-white' : 'bg-violet-50 text-violet-700 hover:bg-violet-100'
      }`
    }
    return `inline-flex h-9 items-center gap-1.5 whitespace-nowrap rounded-full px-4 text-sm font-medium transition-colors ${
      active ? 'bg-slate-100 text-slate-950' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950'
    }`
  }

  const mobileClass = (path: string) => `inline-flex h-10 items-center justify-center gap-1.5 text-xs ${
    pathname === path ? 'font-semibold text-violet-700' : 'font-medium text-slate-600'
  }`

  return (
    <header className="sticky top-0 z-50 border-b border-black/[0.07] bg-white sm:bg-white/95 sm:backdrop-blur-md">
      <div className="mx-auto flex h-[60px] max-w-7xl items-center gap-2 px-3 sm:h-[68px] sm:gap-4 sm:px-6 lg:px-8">
        <a href="https://novatekku.com/" className="flex shrink-0 items-center gap-2.5" aria-label="Novatekku home">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-slate-950 text-xs font-semibold text-white">N</span>
          <span className="hidden text-sm font-semibold tracking-[0.16em] sm:block">NOVA AI</span>
        </a>

        <nav className="ml-6 hidden items-center gap-2 lg:flex">
          <Link to="/assessment" className={navClass('/assessment', true)}>
            <ClipboardCheck className="h-4 w-4" />
            {copy.assessment}
          </Link>
          <Link to="/prices" className={navClass('/prices')}>
            <Tags className="h-4 w-4" />
            {copy.prices}
          </Link>
          <Link to="/stores" className={navClass('/stores')}>
            <Store className="h-4 w-4" />
            {copy.stores}
          </Link>
        </nav>

        <div className="ml-auto flex min-w-0 items-center gap-1 sm:gap-2">
          <select
            value={language}
            onChange={(event) => setLanguage(event.target.value as Language)}
            aria-label={t('languageLabel')}
            className="h-9 w-10 shrink-0 rounded-full border border-slate-200 bg-white px-0.5 text-center text-[10px] text-slate-600 outline-none focus:border-slate-400 sm:w-auto sm:px-3 sm:text-xs"
          >
            <option value="ja">JA</option>
            <option value="zh">中</option>
            <option value="en">EN</option>
          </select>
          {member.data ? (
            <>
              {member.data.is_admin && (
                <Link to="/admin" className="inline-flex h-9 shrink-0 items-center rounded-full px-2 text-[11px] font-medium text-violet-700 hover:bg-violet-50 sm:px-3 sm:text-sm">
                  Admin
                </Link>
              )}
              <Link to="/members/me" className="inline-flex h-9 min-w-0 max-w-24 items-center truncate rounded-full bg-slate-950 px-2.5 text-[11px] font-semibold text-white hover:bg-slate-800 sm:max-w-40 sm:px-4 sm:text-sm">
                {member.data.username}
              </Link>
            </>
          ) : (
            <>
              <Link to="/members/login" className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-1.5 text-[11px] font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-950 sm:px-3 sm:text-sm">
                <LogIn className="hidden h-4 w-4 sm:block" />
                {copy.login}
              </Link>
              {authStatus.data?.enabled !== false && (
                <Link to="/members/register" className="inline-flex h-9 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full bg-slate-950 px-2.5 text-[11px] font-semibold text-white transition-colors hover:bg-slate-800 sm:px-4 sm:text-sm">
                  <UserPlus className="hidden h-4 w-4 sm:block" />
                  {copy.register}
                </Link>
              )}
            </>
          )}
        </div>
      </div>

      <nav className="grid grid-cols-3 border-t border-slate-100 bg-white px-3 lg:hidden">
        <Link to="/assessment" className={mobileClass('/assessment')}>
          <ClipboardCheck className="h-3.5 w-3.5" />
          {copy.assessment}
        </Link>
        <Link to="/prices" className={mobileClass('/prices')}>
          <Tags className="h-3.5 w-3.5" />
          {copy.prices}
        </Link>
        <Link to="/stores" className={mobileClass('/stores')}>
          <Store className="h-3.5 w-3.5" />
          {copy.stores}
        </Link>
      </nav>
    </header>
  )
}
