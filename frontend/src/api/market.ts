import { api } from './client'
import type { QuoteData, NewsItem, RawSignal } from '../types'

export const getQuote = (ticker: string) => api.get<QuoteData>(`/market/quote/${ticker}`)
export const getNews = (ticker?: string) =>
  api.get<NewsItem[]>('/market/news', { params: ticker ? { ticker } : {} })
export const getLiveSignals = () =>
  api.get<{ signals: RawSignal[]; count: number }>('/signals/live')
export const injectSignal = (data: object) => api.post('/dev/inject-signal', data)
