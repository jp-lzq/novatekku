import { FormEvent, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, KeyRound, Mail, UserRound } from 'lucide-react'
import { apiPost } from '../lib/api'
import { getMemberAuthStatus, memberAuthStatusQueryKey } from '../lib/memberAuth'
import { type MemberProfile } from '../lib/member'
import { useI18n } from '../i18n'
import { LightPage, PageHeader, lightPanelClass } from '../components/PageChrome'

function getErrorKey(error: unknown) {
  const response = (error as { response?: { status?: number; data?: { detail?: string } } }).response
  const detail = response?.data?.detail ?? ''

  if (response?.status === 409 && detail.includes('Email')) return 'memberRegisterErrorEmail'
  if (response?.status === 409 && detail.includes('Username')) return 'memberRegisterErrorUsername'
  if (response?.status === 422) return 'memberRegisterErrorValidation'
  if (response?.status === 429) return 'memberAuthRateLimited'
  if (response?.status === 503) return 'memberAuthPausedDescription'
  return 'memberRegisterErrorGeneric'
}

export default function MemberRegister() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [member, setMember] = useState<MemberProfile | null>(null)
  const [errorKey, setErrorKey] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const authStatus = useQuery({
    queryKey: memberAuthStatusQueryKey,
    queryFn: getMemberAuthStatus,
    staleTime: 15_000,
    retry: false,
  })

  if (authStatus.data?.enabled === false) {
    return (
      <LightPage>
        <PageHeader title={t('memberRegisterNav')} />
        <main className="mx-auto max-w-3xl px-3 py-4 sm:px-4 sm:py-10">
          <section className={`border-t-2 border-t-amber-500 p-5 sm:p-9 ${lightPanelClass}`}>
            <AlertTriangle className="h-7 w-7 text-amber-600" />
            <h2 className="mt-4 text-2xl font-semibold text-slate-950">{t('memberAuthPausedTitle')}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">{t('memberAuthPausedDescription')}</p>
          </section>
        </main>
      </LightPage>
    )
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorKey(null)
    setMember(null)

    if (password !== passwordConfirm) {
      setErrorKey('memberRegisterErrorPasswordMismatch')
      return
    }

    setIsSubmitting(true)

    try {
      const data = await apiPost<MemberProfile>('/api/v1/members/register', {
        username,
        email,
        password,
      })
      setMember(data)
      queryClient.setQueryData(['current-member'], data)
      setUsername('')
      setEmail('')
      setPassword('')
      setPasswordConfirm('')
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
      <PageHeader title={t('memberRegisterNav')} />

      <main className="mx-auto max-w-3xl px-3 py-4 sm:px-4 sm:py-10">
        <section className={`border-t-2 border-t-cyan-500 p-5 sm:p-9 ${lightPanelClass}`}>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-700">
            {t('memberRegisterEyebrow')}
          </p>
          <h2 className="mt-3 text-2xl font-semibold text-slate-950">{t('memberRegisterTitle')}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">{t('memberRegisterDescription')}</p>

          <form onSubmit={handleSubmit} className="mt-8 grid gap-5">
            <label className="grid gap-2">
              <span className="text-sm font-medium text-slate-800">{t('memberUsername')}</span>
              <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-[#f8f9fc] px-4 py-3 focus-within:border-cyan-500 focus-within:ring-2 focus-within:ring-cyan-100">
                <UserRound className="h-5 w-5 text-slate-400" />
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                  placeholder={t('memberUsernamePlaceholder')}
                  minLength={2}
                  maxLength={50}
                  required
                />
              </div>
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-medium text-slate-800">{t('memberEmail')}</span>
              <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-[#f8f9fc] px-4 py-3 focus-within:border-cyan-500 focus-within:ring-2 focus-within:ring-cyan-100">
                <Mail className="h-5 w-5 text-slate-400" />
                <input
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                  placeholder={t('memberEmailPlaceholder')}
                  type="email"
                  maxLength={255}
                  required
                />
              </div>
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-medium text-slate-800">{t('memberPassword')}</span>
              <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-[#f8f9fc] px-4 py-3 focus-within:border-cyan-500 focus-within:ring-2 focus-within:ring-cyan-100">
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

            <label className="grid gap-2">
              <span className="text-sm font-medium text-slate-800">{t('memberPasswordConfirm')}</span>
              <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-[#f8f9fc] px-4 py-3 focus-within:border-cyan-500 focus-within:ring-2 focus-within:ring-cyan-100">
                <KeyRound className="h-5 w-5 text-slate-400" />
                <input
                  value={passwordConfirm}
                  onChange={(event) => setPasswordConfirm(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                  placeholder={t('memberPasswordConfirmPlaceholder')}
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
              className="inline-flex items-center justify-center rounded-xl bg-slate-950 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-cyan-700 disabled:bg-slate-300"
            >
              {isSubmitting ? t('memberRegisterSubmitting') : t('memberRegisterSubmit')}
            </button>
          </form>

          {member && (
            <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5" />
                <div>
                  <p className="font-semibold">{t('memberRegisterSuccessTitle')}</p>
                  <p className="mt-1 leading-6">
                    {t('memberRegisterSuccessDescription', { username: member.username })}
                  </p>
                  <Link to="/members/me" className="mt-3 inline-flex font-medium text-emerald-900 hover:underline">
                    {t('memberGoToMyPage')}
                  </Link>
                </div>
              </div>
            </div>
          )}

          {errorKey && (
            <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm leading-6 text-rose-700">
              {t(errorKey)}
            </div>
          )}

          <div className="mt-6 text-sm text-slate-600">
            {t('memberRegisterHasAccount')}{' '}
            <Link to="/members/login" className="font-medium text-slate-950 hover:underline">
              {t('memberLoginNav')}
            </Link>
          </div>
        </section>
      </main>
    </LightPage>
  )
}
