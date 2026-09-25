import { FormEvent, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { AlertTriangle, KeyRound, LogIn, Mail } from 'lucide-react'
import { apiPost } from '../lib/api'
import { getMemberAuthStatus, memberAuthStatusQueryKey } from '../lib/memberAuth'
import type { MemberProfile } from '../lib/member'
import { useI18n } from '../i18n'
import { LightPage, PageHeader, lightPanelClass } from '../components/PageChrome'

function getErrorKey(error: unknown) {
  const response = (error as { response?: { status?: number } }).response
  if (response?.status === 503) return 'memberAuthPausedDescription'
  if (response?.status === 401) return 'memberLoginErrorGeneric'
  if (response?.status === 429) return 'memberAuthRateLimited'
  if (response?.status === 422) return 'memberRegisterErrorValidation'
  return 'memberLoginErrorGeneric'
}

export default function MemberLogin() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [errorKey, setErrorKey] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const authStatus = useQuery({
    queryKey: memberAuthStatusQueryKey,
    queryFn: getMemberAuthStatus,
    staleTime: 15_000,
    retry: false,
  })
  const adminLogin = searchParams.get('admin') === '1'
  const showLoginForm = adminLogin || authStatus.data?.enabled !== false

  if (!showLoginForm) {
    return (
      <LightPage>
        <PageHeader title={t('memberLoginNav')} />
        <main className="mx-auto max-w-3xl px-3 py-4 sm:px-4 sm:py-10">
          <section className={`border-t-2 border-t-amber-500 p-5 sm:p-9 ${lightPanelClass}`}>
            <AlertTriangle className="h-7 w-7 text-amber-600" />
            <h2 className="mt-4 text-2xl font-semibold text-slate-950">{t('memberAuthPausedTitle')}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">{t('memberAuthPausedDescription')}</p>
            <Link
              to="/members/login?admin=1"
              className="mt-5 inline-flex min-h-11 items-center justify-center rounded-xl border border-slate-300 bg-white px-4 text-sm font-medium text-slate-700 hover:border-slate-400 hover:text-slate-950"
            >
              {t('memberAdminPanel')}
            </Link>
          </section>
        </main>
      </LightPage>
    )
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorKey(null)
    setIsSubmitting(true)

    try {
      const member = await apiPost<MemberProfile>('/api/v1/members/login', { identifier, password })
      queryClient.setQueryData(['current-member'], member)
      navigate('/members/me')
    } catch (error) {
      if ((error as { response?: { status?: number } }).response?.status === 503) {
        queryClient.setQueryData(memberAuthStatusQueryKey, { enabled: false })
      }
      setErrorKey(getErrorKey(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <LightPage>
      <PageHeader title={t('memberLoginNav')} />

      <main className="mx-auto max-w-3xl px-3 py-4 sm:px-4 sm:py-10">
        <section className={`border-t-2 border-t-violet-500 p-5 sm:p-9 ${lightPanelClass}`}>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
            {t('memberLoginEyebrow')}
          </p>
          <h2 className="mt-3 text-2xl font-semibold text-slate-950">{t('memberLoginTitle')}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">{t('memberLoginDescription')}</p>

          <form onSubmit={handleSubmit} className="mt-8 grid gap-5">
            <label className="grid gap-2">
              <span className="text-sm font-medium text-slate-800">{t('memberLoginIdentifier')}</span>
              <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-[#f8f9fc] px-4 py-3 focus-within:border-violet-400 focus-within:ring-2 focus-within:ring-violet-100">
                <Mail className="h-5 w-5 text-slate-400" />
                <input
                  value={identifier}
                  onChange={(event) => setIdentifier(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                  placeholder={t('memberLoginIdentifierPlaceholder')}
                  type="text"
                  maxLength={255}
                  required
                />
              </div>
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-medium text-slate-800">{t('memberPassword')}</span>
              <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-[#f8f9fc] px-4 py-3 focus-within:border-violet-400 focus-within:ring-2 focus-within:ring-violet-100">
                <KeyRound className="h-5 w-5 text-slate-400" />
                <input
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                  placeholder={t('memberPasswordPlaceholder')}
                  type="password"
                  minLength={8}
                  maxLength={128}
                  required
                />
              </div>
            </label>

            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-violet-700 disabled:bg-slate-300"
            >
              <LogIn className="h-4 w-4" />
              {isSubmitting ? t('memberLoginSubmitting') : t('memberLoginSubmit')}
            </button>
          </form>

          {errorKey && (
            <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm leading-6 text-rose-700">
              {t(errorKey)}
            </div>
          )}

          {authStatus.data?.enabled !== false && (
            <div className="mt-6 text-sm text-slate-600">
              {t('memberLoginNoAccount')}{' '}
              <Link to="/members/register" className="font-medium text-slate-950 hover:underline">
                {t('memberRegisterNav')}
              </Link>
            </div>
          )}
          <div className="mt-3 text-sm">
            <Link to="/members/reset-password" className="font-medium text-slate-950 hover:underline">
              {t('memberForgotPassword')}
            </Link>
          </div>
        </section>
      </main>
    </LightPage>
  )
}
