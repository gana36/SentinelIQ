import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getTradeTokenInfo, confirmTradeByToken } from '../api/trade'
import type { TradeDraft, TokenInfo } from '../api/trade'
import { Loader2, X, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react'

type Stage = 'loading' | 'error' | 'review' | 'executing' | 'done'

export function TradeConfirm() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''

  const [stage, setStage] = useState<Stage>('loading')
  const [errorMsg, setErrorMsg] = useState('')
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null)
  const [result, setResult] = useState<TradeDraft | null>(null)

  // Order editor state
  const [action, setAction] = useState<'buy' | 'sell'>('buy')
  const [shares, setShares] = useState(1)

  // Alpaca keys — auto-populated from localStorage
  const [alpacaKey, setAlpacaKey] = useState(() => localStorage.getItem('alpaca_key') ?? '')
  const [alpacaSecret, setAlpacaSecret] = useState(() => localStorage.getItem('alpaca_secret') ?? '')
  const [showKey, setShowKey] = useState(false)
  const [showSecret, setShowSecret] = useState(false)
  const [showKeys, setShowKeys] = useState(false)

  useEffect(() => {
    if (!token) { setErrorMsg('No trade token found in URL.'); setStage('error'); return }
    getTradeTokenInfo(token)
      .then(r => {
        setTokenInfo(r.data)
        setAction(r.data.action)
        setShares(r.data.shares)
        setStage('review')
      })
      .catch(err => {
        const msg = err?.response?.data?.detail ?? 'Invalid or expired trade link.'
        setErrorMsg(msg)
        setStage('error')
      })
  }, [token])

  const handleConfirm = async () => {
    if (!tokenInfo) return
    setStage('executing')
    try {
      const res = await confirmTradeByToken({
        token,
        action,
        shares,
        alpaca_key: alpacaKey || undefined,
        alpaca_secret: alpacaSecret || undefined,
      })
      setResult(res.data)
      setStage('done')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErrorMsg(detail ?? 'Trade execution failed.')
      setStage('error')
    }
  }

  const actionColor = action === 'buy' ? '#10B981' : '#EF4444'

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: 'Inter, system-ui, sans-serif' }}>
      {/* Topbar */}
      <div style={{ position: 'fixed', top: 0, left: 0, right: 0, height: 56, background: 'white', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', padding: '0 24px', gap: 8, zIndex: 10 }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#10B981', marginRight: 2 }} />
        <span style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.3px' }}>SentinelIQ</span>
        <span style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 500 }}>Market Intelligence</span>
      </div>

      <div style={{ maxWidth: 440, width: '100%', margin: '0 16px', marginTop: 56 }}>

        {/* Loading */}
        {stage === 'loading' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, padding: 48 }}>
            <Loader2 style={{ width: 32, height: 32, color: '#10B981', animation: 'spin 1s linear infinite' }} />
            <p style={{ color: '#64748b', fontSize: 14 }}>Verifying trade link…</p>
          </div>
        )}

        {/* Error */}
        {stage === 'error' && (
          <div style={{ background: 'white', border: '1px solid #fecaca', borderRadius: 12, padding: '40px 36px', textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
            <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#fef2f2', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
              <AlertCircle style={{ width: 28, height: 28, color: '#EF4444' }} />
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', marginBottom: 10 }}>
              {errorMsg.includes('already') ? 'Link Already Used' : 'Invalid Trade Link'}
            </h2>
            <p style={{ fontSize: 14, color: '#64748b', lineHeight: 1.6 }}>{errorMsg}</p>
          </div>
        )}

        {/* Review / Order Editor */}
        {(stage === 'review' || stage === 'executing') && tokenInfo && (
          <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 12, padding: '40px 36px', boxShadow: '0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)' }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>Review Your Order</h2>
            <p style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 500, marginBottom: 28 }}>${tokenInfo.ticker} — Alpaca Paper Trade</p>

            {/* Buy / Sell toggle */}
            <label style={{ display: 'block', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: 8 }}>Order Type</label>
            <div style={{ display: 'flex', border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'hidden', marginBottom: 20 }}>
              {(['buy', 'sell'] as const).map(a => (
                <button key={a} onClick={() => setAction(a)}
                  style={{ flex: 1, padding: '10px', fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', cursor: 'pointer', border: 'none', transition: 'all 0.15s',
                    background: action === a ? (a === 'buy' ? '#10B981' : '#EF4444') : 'white',
                    color: action === a ? 'white' : '#64748b' }}>
                  {a}
                </button>
              ))}
            </div>

            {/* Shares */}
            <label style={{ display: 'block', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: 8 }}>Number of Shares</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 24 }}>
              <button onClick={() => setShares(s => Math.max(1, s - 1))}
                style={{ width: 36, height: 36, border: '1px solid #e2e8f0', borderRadius: 8, background: 'white', fontSize: 18, fontWeight: 700, color: '#475569', cursor: 'pointer' }}>−</button>
              <input type="number" min={1} max={9999} value={shares}
                onChange={e => setShares(Math.max(1, parseInt(e.target.value) || 1))}
                style={{ flex: 1, textAlign: 'center', fontSize: 18, fontWeight: 700, color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 8, padding: '8px', outline: 'none' }} />
              <button onClick={() => setShares(s => s + 1)}
                style={{ width: 36, height: 36, border: '1px solid #e2e8f0', borderRadius: 8, background: 'white', fontSize: 18, fontWeight: 700, color: '#475569', cursor: 'pointer' }}>+</button>
            </div>

            {/* Alpaca Keys — auto-populated if saved in Settings */}
            <button onClick={() => setShowKeys(v => !v)}
              style={{ fontSize: 11, color: '#94a3b8', cursor: 'pointer', background: 'none', border: 'none', padding: 0, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600, letterSpacing: '0.05em' }}>
              {showKeys ? '▲' : '▼'} {alpacaKey ? 'Alpaca keys loaded from Settings' : 'Use your own Alpaca keys (optional)'}
            </button>
            {showKeys && (
              <div style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, marginBottom: 20, background: '#f8fafc' }}>
                {alpacaKey && (
                  <p style={{ fontSize: 11, color: '#10B981', fontWeight: 600, marginBottom: 10 }}>
                    Keys auto-loaded from your Settings page.
                  </p>
                )}
                <label style={{ display: 'block', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: 6 }}>API Key ID</label>
                <div style={{ position: 'relative', marginBottom: 10 }}>
                  <input type={showKey ? 'text' : 'password'} placeholder="PK..." value={alpacaKey}
                    onChange={e => setAlpacaKey(e.target.value)}
                    style={{ width: '100%', fontSize: 13, color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 6, padding: '8px 36px 8px 10px', outline: 'none', background: 'white', fontFamily: 'monospace', boxSizing: 'border-box' }} />
                  <button type="button" onClick={() => setShowKey(v => !v)}
                    style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: 0 }}>
                    {showKey ? <EyeOff style={{ width: 14, height: 14 }} /> : <Eye style={{ width: 14, height: 14 }} />}
                  </button>
                </div>
                <label style={{ display: 'block', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#94a3b8', marginBottom: 6 }}>Secret Key</label>
                <div style={{ position: 'relative', marginBottom: 8 }}>
                  <input type={showSecret ? 'text' : 'password'} placeholder="••••••••" value={alpacaSecret}
                    onChange={e => setAlpacaSecret(e.target.value)}
                    style={{ width: '100%', fontSize: 13, color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 6, padding: '8px 36px 8px 10px', outline: 'none', background: 'white', fontFamily: 'monospace', boxSizing: 'border-box' }} />
                  <button type="button" onClick={() => setShowSecret(v => !v)}
                    style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8', padding: 0 }}>
                    {showSecret ? <EyeOff style={{ width: 14, height: 14 }} /> : <Eye style={{ width: 14, height: 14 }} />}
                  </button>
                </div>
                <p style={{ fontSize: 11, color: '#94a3b8' }}>Leave blank to use system paper trading account.</p>
              </div>
            )}

            <button onClick={handleConfirm} disabled={stage === 'executing'}
              style={{ width: '100%', padding: 13, border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', cursor: stage === 'executing' ? 'not-allowed' : 'pointer', color: 'white', background: actionColor, opacity: stage === 'executing' ? 0.7 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              {stage === 'executing' && <Loader2 style={{ width: 16, height: 16, animation: 'spin 1s linear infinite' }} />}
              {stage === 'executing' ? 'Placing Order…' : `${action.toUpperCase()} ${shares} share${shares !== 1 ? 's' : ''} of $${tokenInfo.ticker}`}
            </button>

            <p style={{ fontSize: 11, color: '#94a3b8', textAlign: 'center', marginTop: 14 }}>
              Paper trade only · No real money · Link expires in 1 hour
            </p>
          </div>
        )}

        {/* Done / Receipt */}
        {stage === 'done' && result && (
          <div style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 12, padding: '40px 36px', textAlign: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)' }}>
            <div style={{ width: 56, height: 56, borderRadius: '50%', background: result.action === 'buy' ? '#f0fdf4' : '#fef2f2', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
              <CheckCircle style={{ width: 28, height: 28, color: result.action === 'buy' ? '#10B981' : '#EF4444' }} />
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', marginBottom: 8 }}>
              Trade Submitted
            </h2>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24, lineHeight: 1.6 }}>
              {result.action.toUpperCase()} {result.shares} share{result.shares !== 1 ? 's' : ''} of ${result.ticker} — a confirmation email is on its way.
            </p>
            <div style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid #e2e8f0', marginBottom: 20, filter: 'grayscale(0.2)' }}>
              <img src={`data:image/svg+xml;base64,${result.screenshot_b64}`} alt="Receipt" style={{ width: '100%', display: 'block' }} />
            </div>
            {result.is_mock && (
              <p style={{ fontSize: 11, color: '#94a3b8' }}>Mock mode — no real Alpaca order was placed.</p>
            )}
          </div>
        )}

        <p style={{ fontSize: 11, color: '#cbd5e1', textAlign: 'center', marginTop: 20 }}>
          Powered by <span style={{ color: '#10B981', fontWeight: 600 }}>SentinelIQ</span> · Amazon Nova
        </p>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        * { box-sizing: border-box; }
        button:hover { opacity: 0.85; }
      `}</style>
    </div>
  )
}
