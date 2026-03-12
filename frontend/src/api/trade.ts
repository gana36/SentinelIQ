import { api } from './client'

export interface DraftRequest {
  ticker: string
  action: 'buy' | 'sell'
  shares: number
  est_price: number
}

export interface ExecuteRequest extends DraftRequest {
  alpaca_key?: string
  alpaca_secret?: string
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

export interface TokenInfo {
  ticker: string
  action: 'buy' | 'sell'
  shares: number
}

export const draftTrade = (data: DraftRequest) =>
  api.post<TradeDraft>('/trade/draft', data)

export const executeTrade = (data: ExecuteRequest) =>
  api.post<TradeDraft>('/trade/execute', data)

export const getTradeTokenInfo = (token: string) =>
  api.get<TokenInfo>(`/trade/token-info?token=${encodeURIComponent(token)}`)

export const confirmTradeByToken = (data: { token: string; action: string; shares: number; alpaca_key?: string; alpaca_secret?: string }) =>
  api.post<TradeDraft>('/trade/confirm-json', data)
