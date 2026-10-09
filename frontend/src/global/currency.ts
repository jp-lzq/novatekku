import { useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useState } from 'react'
import { apiGet } from '../lib/api'

export type Currency = 'JPY' | 'HKD' | 'USD' | 'CNY' | 'EUR'

export const CURRENCIES: Currency[] = ['JPY', 'HKD', 'USD', 'CNY', 'EUR']

const SYMBOLS: Record<Currency, string> = { JPY: '¥', HKD: 'HK$', USD: '$', CNY: 'CN¥', EUR: '€' }

interface FxResponse {
  rates: Partial<Record<Exclude<Currency, 'JPY'>, { rate: number }>>
  last_updated?: string
}

/** Yen per one unit of each currency, from the hourly rate feed. */
export function useFxRates() {
  const query = useQuery<FxResponse>({
    queryKey: ['fx'],
    queryFn: () => apiGet<FxResponse>('/api/v1/fx'),
    staleTime: 1000 * 60 * 30,
    refetchOnWindowFocus: false,
  })
  const rates: Partial<Record<Currency, number>> = { JPY: 1 }
  for (const [code, value] of Object.entries(query.data?.rates ?? {})) {
    if (value && value.rate > 0) rates[code as Currency] = value.rate
  }
  return { rates, updatedAt: query.data?.last_updated, isLoading: query.isLoading }
}

export function convert(amount: number, from: Currency, to: Currency, rates: Partial<Record<Currency, number>>) {
  if (from === to) return amount
  const fromRate = rates[from]
  const toRate = rates[to]
  if (!fromRate || !toRate) return null
  return (amount * fromRate) / toRate
}

export function formatMoney(amount: number, currency: Currency, signed = false) {
  const sign = signed ? (amount > 0 ? '+' : amount < 0 ? '-' : '±') : amount < 0 ? '-' : ''
  const value = Math.round(Math.abs(amount)).toLocaleString('en-US')
  return `${sign}${SYMBOLS[currency]}${value}`
}

const STORAGE_KEY = 'nova.global.currency'

/**
 * Display currency: follows the market tab until the user picks one manually;
 * the manual choice then sticks across tabs ("auto" clears it).
 */
export function useDisplayCurrency(marketDefault: Currency) {
  const [manual, setManual] = useState<Currency | null>(() => {
    const stored = typeof window === 'undefined' ? null : window.localStorage.getItem(STORAGE_KEY)
    return stored && (CURRENCIES as string[]).includes(stored) ? (stored as Currency) : null
  })

  useEffect(() => {
    if (manual) window.localStorage.setItem(STORAGE_KEY, manual)
    else window.localStorage.removeItem(STORAGE_KEY)
  }, [manual])

  const choose = useCallback((value: Currency | 'auto') => setManual(value === 'auto' ? null : value), [])
  return { currency: manual ?? marketDefault, manual, choose }
}
