import { Navigate, useParams, useSearchParams } from 'react-router-dom'

/** Old detail URLs (/global/<model>) now open the same model on the one-page view. */
export default function GlobalRedirect() {
  const { slug = '' } = useParams()
  const [params] = useSearchParams()
  const next = new URLSearchParams(params)
  next.set('model', slug)
  return <Navigate to={`/global?${next.toString()}`} replace />
}

