import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Filter } from 'lucide-react'
import { getAlerts } from '../api/alerts'
import { ActionCard } from '../components/alerts/ActionCard'
import { Spinner } from '../components/ui/Spinner'
import { useStore } from '../store'

export function Alerts() {
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const { resetUnread } = useStore()
  const qc = useQueryClient()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['alerts', filter],
    queryFn: () => getAlerts(0, 50).then(r => r.data),
    onSuccess: () => resetUnread(),
  } as any)

  const alerts = (data ?? []).filter((a: any) => filter === 'all' || !a.read_at)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-emerald-400" />
          <h1 className="text-2xl font-bold">Alerts</h1>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          {(['all', 'unread'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors capitalize
                ${filter === f ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : 'btn-ghost'}`}>
              {f}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <div className="flex justify-center py-12"><Spinner size="lg" /></div>}

      {!isLoading && alerts.length === 0 && (
        <div className="card text-center py-16 text-slate-500">
          <Bell className="w-10 h-10 mx-auto mb-3 opacity-20" />
          <p>No {filter === 'unread' ? 'unread ' : ''}alerts yet</p>
        </div>
      )}

      <div className="space-y-3">
        {alerts.map((alert: any) => (
          <ActionCard key={alert.id} alert={alert} onRead={() => { refetch(); qc.invalidateQueries({ queryKey: ['alerts'] }) }} />
        ))}
      </div>
    </div>
  )
}
