import { api } from './client'

export const login = (email: string, password: string) =>
  api.post<{ access_token: string }>('/auth/login', { email, password })

export const register = (email: string, password: string) =>
  api.post<{ access_token: string }>('/auth/register', { email, password })

export const getMe = () => api.get('/users/me')
export const getPreferences = () => api.get('/users/me/preferences')
export const updatePreferences = (data: object) => api.patch('/users/me/preferences', data)
