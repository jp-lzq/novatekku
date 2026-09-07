import axios from 'axios'
import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import {
  Bell,
  Bookmark,
  CheckCircle2,
  History,
  KeyRound,
  LogOut,
  Mail,
  Save,
  ShieldCheck,
  UserRound,
} from 'lucide-react'
import {
  changeMemberPassword,
  getCurrentMember,
  logoutMember,
  updateMemberProfile,
} from '../lib/member'
import { useI18n, type Language } from '../i18n'
import { LightPage, PageHeader, lightPanelClass } from '../components/PageChrome'

function formatDateTime(value: string, language: Language) {
  return new Intl.DateTimeFormat(
    language === 'ja' ? 'ja-JP' : language === 'zh' ? 'zh-CN' : 'en-US',
    {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    },
  ).format(new Date(value))
}

function getMemberUpdateErrorKey(error: unknown, action: 'profile' | 'password') {
  if (!axios.isAxiosError(error)) {
    return action === 'profile' ? 'memberProfileUpdateError' : 'memberPasswordUpdateError'
  }

  const status = error.response?.status
  const detail = String(error.response?.data?.detail ?? '')
  if (status === 429) return 'memberAuthRateLimited'
  if (status === 401 && detail.includes('Current password')) return 'memberCurrentPasswordInvalid'
  if (status === 401) return 'memberSessionExpired'
  if (status === 409 && detail.includes('Username')) return 'memberUsernameTaken'
  if (status === 409 && detail.includes('Email')) return 'memberEmailTaken'
  if (status === 409) return 'memberAccountConflict'
  if (status === 422) {
    return action === 'profile' ? 'memberAccountValidation' : 'memberPasswordValidation'
  }
  return action === 'profile' ? 'memberProfileUpdateError' : 'memberPasswordUpdateError'
}

export default function MemberProfile() {
  const { language, t } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [profilePassword, setProfilePassword] = useState('')
  const [profileErrorKey, setProfileErrorKey] = useState<string | null>(null)
  const [profileUpdated, setProfileUpdated] = useState(false)
  const [isSavingProfile, setIsSavingProfile] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('')
  const [passwordErrorKey, setPasswordErrorKey] = useState<string | null>(null)
  const [isSavingPassword, setIsSavingPassword] = useState(false)
  const [passwordChanged, setPasswordChanged] = useState(false)

  const { data: member, isLoading } = useQuery({
    queryKey: ['current-member'],
    queryFn: getCurrentMember,
    staleTime: 1000 * 60 * 5,
    retry: false,
  })

  useEffect(() => {
    if (!member) return
    setUsername(member.username)
    setEmail(member.email)
  }, [member])

  const futureItems = useMemo(
    () => [
      { icon: Bookmark, title: t('memberSavedModels'), description: t('memberSavedModelsDescription') },
      { icon: Bell, title: t('memberPriceAlerts'), description: t('memberPriceAlertsDescription') },
      { icon: History, title: t('memberConsultHistory'), description: t('memberConsultHistoryDescription') },
    ],
    [t],
  )

  const profileChanged = Boolean(
    member
    && (
      (!member.is_admin && username.trim() !== member.username)
      || email.trim().toLowerCase() !== member.email.toLowerCase()
    ),
  )

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await logoutMember()
      queryClient.setQueryData(['current-member'], null)
      navigate('/')
    } finally {
      setIsLoggingOut(false)
    }
  }

  const handleProfileSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setProfileErrorKey(null)
    setProfileUpdated(false)
    setIsSavingProfile(true)

    try {
      const updatedMember = await updateMemberProfile({
        username,
        email,
        current_password: profilePassword,
      })
      queryClient.setQueryData(['current-member'], updatedMember)
      setUsername(updatedMember.username)
      setEmail(updatedMember.email)
      setProfilePassword('')
      setProfileUpdated(true)
    } catch (error) {
      setProfileErrorKey(getMemberUpdateErrorKey(error, 'profile'))
    } finally {
      setIsSavingProfile(false)
    }
  }

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setPasswordErrorKey(null)

    if (newPassword !== newPasswordConfirm) {
      setPasswordErrorKey('memberPasswordMismatch')
      return
    }

    setIsSavingPassword(true)
    try {
      await changeMemberPassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      queryClient.setQueryData(['current-member'], null)
      setPasswordChanged(true)
    } catch (error) {
      setPasswordErrorKey(getMemberUpdateErrorKey(error, 'password'))
    } finally {
      setIsSavingPassword(false)
    }
  }

  if (isLoading) {
    return (
      <LightPage>
        <main className="mx-auto max-w-4xl px-4 py-16 text-center text-sm text-slate-500">
          {t('memberSessionChecking')}
        </main>
      </LightPage>
    )
  }

  if (passwordChanged) {
    return (
      <LightPage>
        <PageHeader title={t('memberMyPageNav')} />
        <main className="mx-auto max-w-xl px-3 py-6 sm:px-4 sm:py-12">
          <section className={'border-t-2 border-t-emerald-500 px-6 py-10 text-center sm:px-8 ' + lightPanelClass}>
            <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-600" />
            <h1 className="mt-5 text-2xl font-semibold text-slate-950">{t('memberPasswordChangedTitle')}</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">{t('memberPasswordChangedDescription')}</p>
            <Link
              to="/members/login"
              className="mt-7 inline-flex items-center justify-center rounded-2xl bg-slate-950 px-6 py-3 text-sm font-medium text-white"
            >
              {t('memberBackToLogin')}
            </Link>
          </section>
        </main>
      </LightPage>
    )
  }

  if (!member) {
    return (
      <LightPage>
        <PageHeader title={t('memberMyPageNav')} />
        <main className="mx-auto max-w-4xl px-3 py-4 sm:px-4 sm:py-10">
          <section className={`border-t-2 border-t-violet-500 px-5 py-8 text-center sm:px-8 ${lightPanelClass}`}>
            <p className="text-lg font-semibold text-slate-950">{t('memberProfileEmptyTitle')}</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">{t('memberProfileEmptyDescription')}</p>
            <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
              <Link
                to="/members/login"
                className="inline-flex items-center justify-center rounded-2xl bg-slate-950 px-5 py-3 text-sm font-medium text-white"
              >
                {t('memberLoginNav')}
              </Link>
              <Link
                to="/members/register"
                className="inline-flex items-center justify-center rounded-2xl border border-slate-300 px-5 py-3 text-sm font-medium text-slate-900"
              >
                {t('memberRegisterNav')}
              </Link>
            </div>
          </section>
        </main>
      </LightPage>
    )
  }

  return (
    <LightPage>
      <PageHeader title={t('memberMyPageNav')} />

      <main className="mx-auto max-w-5xl px-3 py-4 sm:px-4 sm:py-10">
        <section className={`border-t-2 border-t-violet-500 p-5 sm:p-8 ${lightPanelClass}`}>
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-950 text-white">
                <UserRound className="h-7 w-7" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {t('memberProfileEyebrow')}
                </p>
                <h2 className="mt-1 text-2xl font-semibold text-slate-950">{member.username}</h2>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="inline-flex w-fit rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                {member.is_admin ? t('memberAdminStatus') : t('memberNormalStatus')}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:border-slate-300 hover:text-slate-950 disabled:opacity-50"
              >
                <LogOut className="h-3.5 w-3.5" />
                {t('memberLogout')}
              </button>
            </div>
          </div>

          <dl className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
              <dt className="text-xs font-medium text-slate-500">{t('memberUsername')}</dt>
              <dd className="mt-2 text-sm font-semibold text-slate-950">{member.username}</dd>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
              <dt className="text-xs font-medium text-slate-500">{t('memberEmail')}</dt>
              <dd className="mt-2 break-all text-sm font-semibold text-slate-950">{member.email}</dd>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
              <dt className="text-xs font-medium text-slate-500">{t('memberRegisteredAt')}</dt>
              <dd className="mt-2 text-sm font-semibold text-slate-950">{formatDateTime(member.created_at, language)}</dd>
            </div>
          </dl>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-violet-50 px-3 py-1.5 text-sm font-medium text-violet-700">
              {t('memberAiRemaining', { count: member.ai_remaining })}
            </span>
            {member.is_admin && (
              <Link to="/admin" className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white">
                {t('memberAdminPanel')}
              </Link>
            )}
          </div>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-2">
          <article className={'border-t-2 border-t-sky-500 p-5 sm:p-6 ' + lightPanelClass}>
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-sky-50 p-2.5 text-sky-700">
                <UserRound className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-950">{t('memberAccountSettings')}</h3>
                <p className="mt-1 text-sm leading-6 text-slate-600">{t('memberAccountSettingsDescription')}</p>
              </div>
            </div>

            <form onSubmit={handleProfileSubmit} className="mt-6 grid gap-4">
              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-800">{t('memberUsername')}</span>
                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 focus-within:border-slate-400">
                  <UserRound className="h-5 w-5 shrink-0 text-slate-400" />
                  <input
                    value={username}
                    onChange={(event) => {
                      setUsername(event.target.value)
                      setProfileUpdated(false)
                    }}
                    className="min-w-0 flex-1 bg-transparent text-base text-slate-900 outline-none placeholder:text-slate-400 disabled:text-slate-500 sm:text-sm"
                    placeholder={t('memberUsernamePlaceholder')}
                    autoComplete="username"
                    minLength={2}
                    maxLength={50}
                    disabled={member.is_admin}
                    required
                  />
                </div>
                {member.is_admin && (
                  <span className="text-xs leading-5 text-slate-500">{t('memberAdminUsernameLocked')}</span>
                )}
              </label>

              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-800">{t('memberEmail')}</span>
                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 focus-within:border-slate-400">
                  <Mail className="h-5 w-5 shrink-0 text-slate-400" />
                  <input
                    value={email}
                    onChange={(event) => {
                      setEmail(event.target.value)
                      setProfileUpdated(false)
                    }}
                    className="min-w-0 flex-1 bg-transparent text-base text-slate-900 outline-none placeholder:text-slate-400 sm:text-sm"
                    placeholder={t('memberEmailPlaceholder')}
                    type="email"
                    autoComplete="email"
                    maxLength={255}
                    required
                  />
                </div>
              </label>

              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-800">{t('memberCurrentPassword')}</span>
                <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 focus-within:border-slate-400">
                  <KeyRound className="h-5 w-5 shrink-0 text-slate-400" />
                  <input
                    value={profilePassword}
                    onChange={(event) => setProfilePassword(event.target.value)}
                    className="min-w-0 flex-1 bg-transparent text-base text-slate-900 outline-none placeholder:text-slate-400 sm:text-sm"
                    placeholder={t('memberCurrentPasswordPlaceholder')}
                    type="password"
                    autoComplete="current-password"
                    minLength={8}
                    maxLength={128}
                    required
                  />
                </div>
              </label>

              <button
                type="submit"
                disabled={isSavingProfile || !profileChanged || !profilePassword}
                className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-950 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-slate-800 disabled:bg-slate-300"
              >
                <Save className="h-4 w-4" />
                {isSavingProfile ? t('memberSaving') : t('memberSaveChanges')}
              </button>
            </form>

            {profileUpdated && (
              <div className="mt-4 flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                {t('memberProfileUpdated')}
              </div>
            )}
            {profileErrorKey && (
              <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-700">
                {t(profileErrorKey)}
              </div>
            )}
          </article>

          <article className={'border-t-2 border-t-amber-500 p-5 sm:p-6 ' + lightPanelClass}>
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-amber-50 p-2.5 text-amber-700">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-950">{t('memberPasswordSettings')}</h3>
                <p className="mt-1 text-sm leading-6 text-slate-600">{t('memberPasswordSettingsDescription')}</p>
              </div>
            </div>

            <form onSubmit={handlePasswordSubmit} className="mt-6 grid gap-4">
              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-800">{t('memberCurrentPassword')}</span>
                <input
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-base text-slate-900 outline-none placeholder:text-slate-400 focus:border-slate-400 sm:text-sm"
                  placeholder={t('memberCurrentPasswordPlaceholder')}
                  type="password"
                  autoComplete="current-password"
                  minLength={8}
                  maxLength={128}
                  required
                />
              </label>

              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-800">{t('memberNewPassword')}</span>
                <input
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-base text-slate-900 outline-none placeholder:text-slate-400 focus:border-slate-400 sm:text-sm"
                  placeholder={t('memberPasswordPlaceholder')}
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  required
                />
              </label>

              <label className="grid gap-2">
                <span className="text-sm font-medium text-slate-800">{t('memberNewPasswordConfirm')}</span>
                <input
                  value={newPasswordConfirm}
                  onChange={(event) => setNewPasswordConfirm(event.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-base text-slate-900 outline-none placeholder:text-slate-400 focus:border-slate-400 sm:text-sm"
                  placeholder={t('memberPasswordConfirmPlaceholder')}
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  required
                />
              </label>

              <button
                type="submit"
                disabled={isSavingPassword}
                className="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-medium text-slate-900 transition-colors hover:bg-slate-50 disabled:text-slate-400"
              >
                <KeyRound className="h-4 w-4" />
                {isSavingPassword ? t('memberPasswordUpdating') : t('memberPasswordUpdate')}
              </button>
            </form>

            {passwordErrorKey && (
              <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-700">
                {t(passwordErrorKey)}
              </div>
            )}
          </article>
        </section>

        <section className="mt-6 grid gap-4 md:grid-cols-3">
          {futureItems.map((item) => (
            <article key={item.title} className={`p-5 ${lightPanelClass}`}>
              <div className="flex items-center justify-between gap-3">
                <item.icon className="h-5 w-5 text-slate-500" />
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500">
                  {t('memberComingSoon')}
                </span>
              </div>
              <h3 className="mt-4 text-base font-semibold text-slate-950">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.description}</p>
            </article>
          ))}
        </section>
      </main>
    </LightPage>
  )
}
