import { api } from './client'

export interface DraftRequest {
  ticker: string
  action: 'buy' | 'sell'
  shares: number
  est_price: number
}

export interface TradeDraft {
  session_id: string
  ticker: string
  action: 'buy' | 'sell'
  shares: number
  est_price: number
  est_total: number
  screenshot_b64: string
  screenshot_mime: string
  is_mock: boolean
}

export const draftTrade = (data: DraftRequest) =>
  api.post<TradeDraft>('/trade/draft', data)

export const executeTrade = (data: DraftRequest) =>
  api.post<TradeDraft>('/trade/execute', data)
