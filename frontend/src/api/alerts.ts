import { api } from './client'
import type { Alert } from '../types'

export const getAlerts = (skip = 0, limit = 50) =>
  api.get<Alert[]>('/alerts', { params: { skip, limit } })

export const getAlert = (id: string) => api.get<Alert>(`/alerts/${id}`)

export const markRead = (id: string) => api.patch(`/alerts/${id}/read`)

export const voiceExplain = (alertId: string, question: string) =>
  api.post('/voice/explain', { alert_id: alertId, question })
