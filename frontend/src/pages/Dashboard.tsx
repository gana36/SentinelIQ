import { useStore } from '../store'
import { ActionCard } from '../components/alerts/ActionCard'
import { SignalFeed } from '../components/signals/SignalFeed'
import { WebSocketStatus } from '../components/ui/WebSocketStatus'
import { useQuery } from '@tanstack/react-query'
import { getAlerts } from '../api/alerts'
import { getLiveSignals } from '../api/market'

export function Dashboard() {
  const liveAlerts = useStore((s) => s.liveAlerts)
  const { data: alertsData } = useQuery({ queryKey: ['alerts'], queryFn: () => getAlerts(0, 5).then(r => r.data) })
  const { data: signalsData } = useQuery({ queryKey: ['signals-count'], queryFn: () => getLiveSignals().then(r => r.data), refetchInterval: 5000 })

  const recentAlerts = (alertsData as any[]) ?? []
  // Deduplicate: don't show DB alerts already visible in the live WebSocket stream
  const liveAlertIds = new Set(liveAlerts.map(a => a.alert_id))
  const dedupedRecent = recentAlerts.filter((a: any) => !liveAlertIds.has(a.payload?.alert_id))
  const positiveCount = recentAlerts.filter((a: any) => a.payload?.sentiment?.label === 'positive').length
  const negativeCount = recentAlerts.filter((a: any) => a.payload?.sentiment?.label === 'negative').length

  return (
    <div className="p-10 space-y-10 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-end justify-between border-b border-slate-100 pb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard</h1>
          <p className="text-sm font-medium text-slate-500 mt-1">Real-time market intelligence streaming</p>
        </div>
        <WebSocketStatus />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Live Alerts', value: liveAlerts.length },
          { label: 'Signals Processed', value: signalsData?.count ?? 0 },
          { label: 'Positive Signals', value: positiveCount },
          { label: 'Negative Signals', value: negativeCount },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white border border-slate-200/80 rounded-xl p-6 shadow-[0_1px_2px_rgba(0,0,0,0,02)]">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">{label}</div>
            <div className="text-3xl font-bold tracking-tight text-slate-900">{value}</div>
          </div>
        ))}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Live Alerts Stream */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-[13px] font-bold uppercase tracking-[0.15em] text-slate-400 flex items-center gap-3 mb-2">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
            Live Activity
          </h2>
          {liveAlerts.length === 0 && recentAlerts.length === 0 && (
            <div className="bg-slate-50/50 border border-dashed border-slate-200 rounded-2xl text-center py-20">
              <p className="text-sm font-semibold text-slate-900">Listening for market signals...</p>
              <p className="text-xs text-slate-400 mt-1.5">Configure your watchlist to begin automated analysis</p>
            </div>
          )}
          {liveAlerts.map((card) => (
            <ActionCard key={card.alert_id} card={card} compact />
          ))}
          {dedupedRecent.slice(0, 3).map((alert: any) => (
            <ActionCard key={alert.id} alert={alert} compact />
          ))}
        </div>

        {/* Signal Feed */}
        <div className="h-[600px]">
          <SignalFeed />
        </div>
      </div>
    </div>
  )
}
