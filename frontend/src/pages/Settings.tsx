import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Settings as SettingsIcon, Zap, Shield } from 'lucide-react'
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
    <div className="p-6 space-y-6 max-w-2xl">
      <div className="flex items-center gap-2">
        <SettingsIcon className="w-5 h-5 text-emerald-400" />
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>

      {/* Alert Preferences */}
      <div className="card space-y-5">
        <div className="flex items-center gap-2 pb-2 border-b border-[#1e2130]">
          <Shield className="w-4 h-4 text-slate-400" />
          <h2 className="font-semibold">Alert Preferences</h2>
        </div>

        <div>
          <label className="text-xs text-slate-400 mb-2 block">Risk Tolerance</label>
          <div className="grid grid-cols-3 gap-2">
            {(['low', 'medium', 'high'] as const).map(r => (
              <button key={r} onClick={() => setRisk(r)}
                className={`py-2 rounded-lg text-sm font-medium capitalize transition-colors border
                  ${currentRisk === r ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'border-[#1e2130] text-slate-400 hover:text-white hover:border-slate-600'}`}>
                {r}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-400 mb-2 flex justify-between">
            <span>Alert Sensitivity</span>
            <span className="font-mono text-emerald-400">{(currentSensitivity * 100).toFixed(0)}%</span>
          </label>
          <input type="range" min="0" max="1" step="0.05" value={currentSensitivity}
            onChange={e => setSensitivity(parseFloat(e.target.value))}
            className="w-full accent-emerald-500 cursor-pointer" />
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>More alerts (noisy)</span><span>Fewer alerts (precise)</span>
          </div>
        </div>

        <button onClick={() => update.mutate({ risk_tolerance: currentRisk, alert_sensitivity: currentSensitivity })}
          disabled={update.isPending} className="btn-primary">
          {update.isPending ? 'Saving...' : 'Save Preferences'}
        </button>
      </div>

      {/* Demo Controls */}
      <div className="card space-y-4 border-yellow-500/20">
        <div className="flex items-center gap-2 pb-2 border-b border-[#1e2130]">
          <Zap className="w-4 h-4 text-yellow-400" />
          <h2 className="font-semibold">Demo Controls</h2>
          <span className="text-xs text-yellow-500/70 bg-yellow-500/10 border border-yellow-500/20 px-2 py-0.5 rounded-full ml-1">MOCK MODE</span>
        </div>
        <p className="text-xs text-slate-400">Inject a scripted market signal to demonstrate the full pipeline.</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Ticker</label>
            <input className="input font-mono uppercase" value={demoTicker} onChange={e => setDemoTicker(e.target.value.toUpperCase())} />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-1 block">Event Type</label>
            <select className="input" value={demoEvent} onChange={e => setDemoEvent(e.target.value)}>
              {['earnings_beat', 'earnings_miss', 'analyst_upgrade', 'macro_event', 'sec_filing'].map(e => (
                <option key={e} value={e}>{e.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
        </div>
        <button onClick={handleInject} disabled={injecting} className="btn-primary flex items-center gap-2 w-full justify-center">
          <Zap className="w-4 h-4" />{injecting ? 'Injecting...' : '⚡ Inject Demo Signal'}
        </button>
      </div>
    </div>
  )
}
