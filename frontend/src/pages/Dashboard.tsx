import { useStore } from '../store'
import { ActionCard } from '../components/alerts/ActionCard'
import { SignalFeed } from '../components/signals/SignalFeed'
import { WebSocketStatus } from '../components/ui/WebSocketStatus'
import { Zap, TrendingUp, TrendingDown, Activity } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { getAlerts } from '../api/alerts'
import { getLiveSignals } from '../api/market'

export function Dashboard() {
  const liveAlerts = useStore((s) => s.liveAlerts)
  const { data: alertsData } = useQuery({ queryKey: ['alerts'], queryFn: () => getAlerts(0, 5).then(r => r.data) })
  const { data: signalsData } = useQuery({ queryKey: ['signals-count'], queryFn: () => getLiveSignals().then(r => r.data), refetchInterval: 5000 })

  const recentAlerts = alertsData ?? []
  const positiveCount = recentAlerts.filter(a => a.payload?.sentiment?.label === 'positive').length
  const negativeCount = recentAlerts.filter(a => a.payload?.sentiment?.label === 'negative').length

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-0.5">Real-time market intelligence</p>
        </div>
        <WebSocketStatus />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Live Alerts', value: liveAlerts.length, icon: Zap, color: 'text-emerald-400' },
          { label: 'Signals Processed', value: signalsData?.count ?? 0, icon: Activity, color: 'text-blue-400' },
          { label: 'Positive Signals', value: positiveCount, icon: TrendingUp, color: 'text-emerald-400' },
          { label: 'Negative Signals', value: negativeCount, icon: TrendingDown, color: 'text-red-400' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-400">{label}</span>
              <Icon className={`w-4 h-4 ${color}`} />
            </div>
            <div className="text-2xl font-bold font-mono">{value}</div>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Alerts Stream */}
        <div className="lg:col-span-2 space-y-3">
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            Live Alerts
          </h2>
          {liveAlerts.length === 0 && recentAlerts.length === 0 && (
            <div className="card text-center py-12 text-slate-500">
              <Zap className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-sm">Waiting for signals...</p>
              <p className="text-xs mt-1">Connect your watchlist to start receiving alerts</p>
            </div>
          )}
          {liveAlerts.map((card) => (
            <ActionCard key={card.alert_id} card={card} compact />
          ))}
          {recentAlerts.slice(0, 3).map((alert) => (
            <ActionCard key={alert.id} alert={alert} compact />
          ))}
        </div>

        {/* Signal Feed */}
        <div className="h-[500px]">
          <SignalFeed />
        </div>
      </div>
    </div>
  )
}
