import { lazy, Suspense, useEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import LanguageSwitcher from './components/LanguageSwitcher'
import SiteFooter from './components/SiteFooter'

const Prices = lazy(() => import('./pages/Prices'))
const Stores = lazy(() => import('./pages/Stores'))
const Assessment = lazy(() => import('./pages/Assessment'))
const MemberRegister = lazy(() => import('./pages/MemberRegister'))
const MemberLogin = lazy(() => import('./pages/MemberLogin'))
const MemberProfile = lazy(() => import('./pages/MemberProfile'))
const MemberResetPassword = lazy(() => import('./pages/MemberResetPassword'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))
const AdminMembers = lazy(() => import('./pages/AdminMembers'))
const AdminMemberDetail = lazy(() => import('./pages/AdminMemberDetail'))
const AdminPrices = lazy(() => import('./pages/AdminPrices'))
const AdminStorePrices = lazy(() => import('./pages/AdminStorePrices'))
const AdminAIHistory = lazy(() => import('./pages/AdminAIHistory'))
const AdminCollectionSources = lazy(() => import('./pages/AdminCollectionSources'))
const AI = lazy(() => import('./pages/AI'))
const AITest = lazy(() => import('./pages/AITest'))
const ProductDetail = lazy(() => import('./pages/ProductDetail'))
const LegalPage = lazy(() => import('./pages/LegalPage'))
const CompanyHome = lazy(() => import('./pages/CompanyHome'))
const DevelopmentLogPage = lazy(() => import('./pages/DevelopmentLogPage'))

const isCompanySite = import.meta.env.VITE_SITE_MODE === 'company'

function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
  }, [pathname])

  return null
}

function App() {
  const { pathname } = useLocation()

  const pageFallback = (
    <main
      aria-busy="true"
      aria-label="Loading"
      className={`min-h-[100dvh] ${isCompanySite ? 'bg-[#07080b]' : 'bg-[#f7f7f8]'}`}
    />
  )

  if (isCompanySite) {
    return (
      <>
        <LanguageSwitcher />
        <ScrollToTop />
        <Suspense fallback={pageFallback}>
          <Routes>
            <Route path="/" element={<CompanyHome />} />
            <Route path="/company" element={<LegalPage />} />
            <Route path="/development" element={<DevelopmentLogPage />} />
            <Route path="/notice" element={<LegalPage />} />
            <Route path="/privacy" element={<LegalPage />} />
            <Route path="/terms" element={<LegalPage />} />
            <Route path="*" element={<CompanyHome />} />
          </Routes>
        </Suspense>
        <SiteFooter />
      </>
    )
  }

  return (
    <>
      <ScrollToTop />
      <Suspense fallback={pageFallback}>
        <Routes>
          <Route path="/" element={<AI />} />
          <Route path="/ai" element={<AI />} />
          <Route path="/test" element={<AITest />} />
          <Route path="/prices" element={<Prices />} />
          <Route path="/stores" element={<Stores />} />
          <Route path="/assessment" element={<Assessment />} />
          <Route path="/members/register" element={<MemberRegister />} />
          <Route path="/members/login" element={<MemberLogin />} />
          <Route path="/members/reset-password" element={<MemberResetPassword />} />
          <Route path="/members/reset-password/confirm" element={<MemberResetPassword />} />
          <Route path="/members/me" element={<MemberProfile />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/admin/members" element={<AdminMembers />} />
          <Route path="/admin/members/:memberId" element={<AdminMemberDetail />} />
          <Route path="/admin/prices" element={<AdminPrices />} />
          <Route path="/admin/prices/:storeId" element={<AdminStorePrices />} />
          <Route path="/admin/ai-history" element={<AdminAIHistory />} />
          <Route path="/admin/collection-sources" element={<AdminCollectionSources />} />
          <Route path="/product/:id" element={<ProductDetail />} />
          <Route path="/company" element={<LegalPage />} />
          <Route path="/notice" element={<LegalPage />} />
          <Route path="/privacy" element={<LegalPage />} />
          <Route path="/terms" element={<LegalPage />} />
        </Routes>
      </Suspense>
      {pathname !== '/' && pathname !== '/ai' && <SiteFooter />}
    </>
  )
}

export default App
