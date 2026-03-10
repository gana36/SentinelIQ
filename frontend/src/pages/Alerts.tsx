import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, Filter, Trash2 } from 'lucide-react'
import { getAlerts, clearAllAlerts } from '../api/alerts'
import { ActionCard } from '../components/alerts/ActionCard'
import { Spinner } from '../components/ui/Spinner'
import { useStore } from '../store'
import toast from 'react-hot-toast'

export function Alerts() {
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const [clearing, setClearing] = useState(false)
  const { resetUnread } = useStore()
  const qc = useQueryClient()

  useEffect(() => { resetUnread() }, [])

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['alerts', filter],
    queryFn: () => getAlerts(0, 50).then(r => r.data),
    onSuccess: () => resetUnread(),
  } as any)

  const alerts = ((data as any[]) ?? []).filter((a: any) => filter === 'all' || !a.read_at)

  const handleClearAll = async () => {
    if (!window.confirm('Dismiss all alerts? This cannot be undone.')) return
    setClearing(true)
    try {
      await clearAllAlerts()
      qc.invalidateQueries({ queryKey: ['alerts'] })
      toast.success('All alerts cleared')
    } catch {
      toast.error('Could not clear alerts')
    } finally {
      setClearing(false)
    }
  }

  const refresh = () => { refetch(); qc.invalidateQueries({ queryKey: ['alerts'] }) }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="w-5 h-5 text-emerald-400" />
          <h1 className="text-2xl font-semibold tracking-tight text-content-primary">Alerts</h1>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-content-secondary" />
          {(['all', 'unread'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors capitalize
                ${filter === f ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20' : 'btn-ghost'}`}>
              {f}
            </button>
          ))}
          {alerts.length > 0 && (
            <button
              onClick={handleClearAll}
              disabled={clearing}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg text-red-400 border border-red-500/20 hover:bg-red-500/10 transition-colors font-medium">
              <Trash2 className="w-3.5 h-3.5" />
              {clearing ? 'Clearing...' : 'Clear All'}
            </button>
          )}
        </div>
      </div>

      {isLoading && <div className="flex justify-center py-12"><Spinner size="lg" /></div>}

      {!isLoading && alerts.length === 0 && (
        <div className="card text-center py-16 text-content-secondary">
          <Bell className="w-10 h-10 mx-auto mb-3 opacity-20" />
          <p>No {filter === 'unread' ? 'unread ' : ''}alerts yet</p>
        </div>
      )}

      <div className="space-y-3">
        {alerts.map((alert: any) => (
          <ActionCard key={alert.id} alert={alert} onRead={refresh} onDelete={refresh} />
        ))}
      </div>
    </div>
  )
}
