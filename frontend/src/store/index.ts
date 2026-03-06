import { create } from 'zustand'
import type { ActionCard, Alert } from '../types'

interface AppState {
  token: string | null
  setToken: (t: string | null) => void

  liveAlerts: ActionCard[]
  addLiveAlert: (a: ActionCard) => void
  clearLiveAlerts: () => void

  wsConnected: boolean
  setWsConnected: (v: boolean) => void

  unreadCount: number
  incrementUnread: () => void
  resetUnread: () => void
}

export const useStore = create<AppState>((set) => ({
  token: localStorage.getItem('token'),
  setToken: (token) => {
    if (token) localStorage.setItem('token', token)
    else localStorage.removeItem('token')
    set({ token })
  },

  liveAlerts: [],
  addLiveAlert: (alert) =>
    set((s) => ({ liveAlerts: [alert, ...s.liveAlerts].slice(0, 50) })),
  clearLiveAlerts: () => set({ liveAlerts: [] }),

  wsConnected: false,
  setWsConnected: (wsConnected) => set({ wsConnected }),

  unreadCount: 0,
  incrementUnread: () => set((s) => ({ unreadCount: s.unreadCount + 1 })),
  resetUnread: () => set({ unreadCount: 0 }),
}))
