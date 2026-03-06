import { api } from './client'
import type { WatchlistItem } from '../types'

export const getWatchlist = () => api.get<WatchlistItem[]>('/watchlist')
export const addTicker = (ticker: string) => api.post<WatchlistItem>('/watchlist', { ticker })
export const removeTicker = (ticker: string) => api.delete(`/watchlist/${ticker}`)
