import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronRight, Database, MessageSquare, Power, RotateCcw, ShieldAlert, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import AdminShell, { dateTime, useAdminAccess } from '../components/AdminShell'
import { apiGet, apiPost } from '../lib/api'
import { getCsrfHeaders } from '../lib/member'
import { memberAuthStatusQueryKey } from '../lib/memberAuth'

interface MemberAuthControlStatus {
  enabled: boolean
  updated_at: string | null
  updated_by: string | null
}

const modules = [
  {
    to: '/admin/members',
    Icon: Users,
    title: '会員管理',
    description: 'ユーザー名、メールアドレス、登録日時、ログイン記録を確認します。',
  },
  {
    to: '/admin/prices',
    Icon: Database,
    title: '価格記録',
    description: '店舗から商品へ進み、公式価格と表データを並べて確認します。',
  },
  {
    to: '/admin/ai-history',
    Icon: MessageSquare,
    title: 'AI記録',
    description: '会員と訪問者の質問、回答、利用日時、IPを確認します。',
  },
]

export default function AdminDashboard() {
  const access = useAdminAccess()
  const queryClient = useQueryClient()
  const memberAuth = useQuery({
    queryKey: ['admin', 'member-auth'],
    queryFn: () => apiGet<MemberAuthControlStatus>('/api/v1/admin/member-auth'),
    enabled: access.data?.is_admin === true,
    staleTime: 10_000,
    retry: false,
  })
  const updateMemberAuth = useMutation({
    mutationFn: (enabled: boolean) => apiPost<MemberAuthControlStatus>(
      '/api/v1/admin/member-auth',
      { enabled },
      { headers: getCsrfHeaders() },
    ),
    onSuccess: (result) => {
      queryClient.setQueryData(['admin', 'member-auth'], result)
      queryClient.setQueryData(memberAuthStatusQueryKey, { enabled: result.enabled })
    },
  })
  const memberAuthEnabled = memberAuth.data?.enabled !== false

  const toggleMemberAuth = () => {
    if (memberAuthEnabled) {
      const confirmed = window.confirm('一般会員のログインと新規登録を緊急停止します。よろしいですか？')
      if (!confirmed) return
    }
    updateMemberAuth.mutate(!memberAuthEnabled)
  }

  return (
    <AdminShell title="データ管理" backTo="/members/me">
      <div>
        <p className="text-xs font-semibold tracking-[0.18em] text-violet-600">NOVA ADMIN</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">管理メニュー</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">確認する項目を選んでください。ここには詳細データを表示しません。</p>
      </div>

      <section className={`mt-6 rounded-2xl border p-5 shadow-sm ${memberAuthEnabled ? 'border-emerald-200 bg-emerald-50/70' : 'border-rose-200 bg-rose-50/80'}`}>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-2xl ${memberAuthEnabled ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}`}>
              <ShieldAlert className="h-5 w-5" />
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="font-semibold text-slate-950">会員ログイン管理</h2>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${memberAuthEnabled ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                  {memberAuth.isLoading ? '確認中' : memberAuthEnabled ? '通常運転中' : '緊急停止中'}
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                緊急時は一般会員のログインと新規登録をすぐ停止できます。管理者ログインは停止中も利用できます。
              </p>
              {memberAuth.data?.updated_at && (
                <p className="mt-1 text-xs text-slate-500">
                  最終更新：{dateTime(memberAuth.data.updated_at)}{memberAuth.data.updated_by ? ` · ${memberAuth.data.updated_by}` : ''}
                </p>
              )}
            </div>
          </div>
          <button
            type="button"
            onClick={toggleMemberAuth}
            disabled={memberAuth.isLoading || updateMemberAuth.isPending}
            className={`inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold text-white transition-colors disabled:cursor-not-allowed disabled:bg-slate-300 ${memberAuthEnabled ? 'bg-rose-600 hover:bg-rose-700' : 'bg-emerald-600 hover:bg-emerald-700'}`}
          >
            {memberAuthEnabled ? <Power className="h-4 w-4" /> : <RotateCcw className="h-4 w-4" />}
            {updateMemberAuth.isPending ? '切り替え中…' : memberAuthEnabled ? '緊急停止' : 'ログインを復旧'}
          </button>
        </div>
        {(memberAuth.isError || updateMemberAuth.isError) && (
          <p className="mt-4 rounded-xl border border-rose-200 bg-white px-4 py-3 text-sm text-rose-700">
            状態を更新できませんでした。ログイン状態を確認して、もう一度お試しください。
          </p>
        )}
      </section>

      <section className="mt-6 grid gap-3 md:grid-cols-3">
        {modules.map(({ to, Icon, title, description }) => (
          <Link key={to} to={to} className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-violet-200 hover:shadow-md">
            <div className="flex items-start gap-4">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-violet-50 text-violet-700"><Icon className="h-5 w-5" /></span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="font-semibold">{title}</h2>
                  <ChevronRight className="h-4 w-4 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-violet-600" />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
              </div>
            </div>
          </Link>
        ))}
      </section>
    </AdminShell>
  )
}
