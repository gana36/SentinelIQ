import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getPreferences, updatePreferences } from '../api/auth'
import { injectSignal } from '../api/market'
import toast from 'react-hot-toast'

export function Settings() {
  const { data: prefs, refetch } = useQuery({ queryKey: ['prefs'], queryFn: () => getPreferences().then(r => r.data) })
  const [risk, setRisk] = useState<string>('')
  const [sensitivity, setSensitivity] = useState<number | ''>('')
  const [demoTicker, setDemoTicker] = useState('TSLA')
  const [demoEvent, setDemoEvent] = useState('earnings_beat')
  const [injecting, setInjecting] = useState(false)

  const update = useMutation({
    mutationFn: (data: object) => updatePreferences(data),
    onSuccess: () => { refetch(); toast.success('Preferences saved') },
    onError: () => toast.error('Failed to save'),
  })

  const handleInject = async () => {
    setInjecting(true)
    try {
      await injectSignal({ ticker: demoTicker, text: `Breaking: Anomalous signal detected for $${demoTicker} — ${demoEvent} event.`, event_type: demoEvent })
      toast.success(`Signal injected for ${demoTicker}!`)
    } catch { toast.error('Injection failed — is the server running?') }
    finally { setInjecting(false) }
  }

  const currentRisk = risk || prefs?.risk_tolerance || 'medium'
  const currentSensitivity = sensitivity !== '' ? Number(sensitivity) : (prefs?.alert_sensitivity ?? 0.5)

  return (
    <div className="p-10 space-y-10 max-w-2xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Settings</h1>
        <p className="text-sm font-medium text-slate-500 mt-1">Global platform preferences and developer tools</p>
      </div>

      {/* Alert Preferences */}
      <div className="card space-y-6">
        <div className="pb-4 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900">Alert Preferences</h2>
        </div>

        <div>
          <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-3 block">Risk Tolerance</label>
          <div className="grid grid-cols-3 gap-3">
            {(['low', 'medium', 'high'] as const).map(r => (
              <button key={r} onClick={() => setRisk(r)}
                className={`py-2 rounded-lg text-[13px] font-semibold capitalize transition-all border
                  ${currentRisk === r ? 'bg-slate-900 text-white border-slate-900 shadow-sm' : 'border-slate-200 text-slate-500 hover:border-slate-400'}`}>
                {r}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-3 flex justify-between">
            <span>Alert Sensitivity</span>
            <span className="font-mono text-slate-900">{(currentSensitivity * 100).toFixed(0)}%</span>
          </label>
          <input type="range" min="0" max="1" step="0.05" value={currentSensitivity}
            onChange={e => setSensitivity(parseFloat(e.target.value))}
            className="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-slate-900" />
          <div className="flex justify-between text-[11px] font-medium text-slate-400 mt-2">
            <span>Maximum Signal Density</span><span>Highly Selective</span>
          </div>
        </div>

        <button onClick={() => update.mutate({ risk_tolerance: currentRisk, alert_sensitivity: currentSensitivity })}
          disabled={update.isPending} className="w-full py-2.5 rounded-lg bg-slate-900 text-white text-sm font-bold hover:bg-slate-800 transition-colors shadow-sm">
          {update.isPending ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>

      {/* Demo Controls */}
      <div className="card space-y-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-900">Demo Controls</h2>
          <span className="text-[10px] font-bold tracking-widest text-slate-400 border border-slate-200 px-2 py-0.5 rounded uppercase">Mock Pipeline</span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 block">Ticker Symbol</label>
            <input className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-bold font-mono uppercase bg-slate-50 focus:bg-white focus:outline-none focus:border-slate-900 transition-colors" value={demoTicker} onChange={e => setDemoTicker(e.target.value.toUpperCase())} />
          </div>
          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 block">Trigger Event</label>
            <select className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-semibold bg-slate-50 focus:bg-white focus:outline-none focus:border-slate-900 transition-colors appearance-none" value={demoEvent} onChange={e => setDemoEvent(e.target.value)}>
              {['earnings_beat', 'earnings_miss', 'analyst_upgrade', 'macro_event', 'sec_filing'].map(e => (
                <option key={e} value={e}>{e.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
        </div>
        <button onClick={handleInject} disabled={injecting} className="w-full py-2.5 rounded-lg border border-slate-200 text-slate-900 text-sm font-bold hover:bg-slate-50 transition-colors">
          {injecting ? 'Injecting...' : 'Inject Signal Pipeline'}
        </button>
      </div>
    </div>
  )
}
