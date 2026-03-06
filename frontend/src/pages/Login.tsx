import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Zap } from 'lucide-react'
import { login, register } from '../api/auth'
import { useStore } from '../store'
import toast from 'react-hot-toast'

export function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('demo@sentineliq.ai')
  const [password, setPassword] = useState('demo1234')
  const [loading, setLoading] = useState(false)
  const { setToken } = useStore()
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const fn = mode === 'login' ? login : register
      const res = await fn(email, password)
      setToken(res.data.access_token)
      navigate('/')
    } catch (err: any) {
      toast.error(err.response?.data?.detail ?? 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0b0f] px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 bg-emerald-500 rounded-2xl flex items-center justify-center mb-4 shadow-[0_0_40px_rgba(16,185,129,0.3)]">
            <Zap className="w-6 h-6 text-black" />
          </div>
          <h1 className="text-2xl font-bold text-white">SentinelIQ</h1>
          <p className="text-slate-400 text-sm mt-1">Autonomous Market Intelligence</p>
        </div>

        <form onSubmit={submit} className="card space-y-4">
          <h2 className="font-semibold text-lg">{mode === 'login' ? 'Sign In' : 'Create Account'}</h2>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Email</label>
            <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Password</label>
            <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Loading...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
          <p className="text-center text-xs text-slate-500">
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button type="button" onClick={() => setMode(m => m === 'login' ? 'register' : 'login')}
              className="text-emerald-400 hover:underline">
              {mode === 'login' ? 'Register' : 'Sign In'}
            </button>
          </p>
          {mode === 'login' && (
            <p className="text-center text-xs text-slate-600">Demo: demo@sentineliq.ai / demo1234</p>
          )}
        </form>
      </div>
    </div>
  )
}
