import { useQuery } from '@tanstack/react-query'
import { Activity } from 'lucide-react'
import { getLiveSignals } from '../../api/market'
import { SourceBadge } from '../ui/SourceBadge'
import { Spinner } from '../ui/Spinner'
import type { RawSignal } from '../../types'

export function SignalFeed() {
  const { data, isLoading } = useQuery({
    queryKey: ['live-signals'],
    queryFn: () => getLiveSignals().then(r => r.data),
    refetchInterval: 5000,
  })

  const signals: RawSignal[] = data?.signals ?? []

  return (
    <div className="card h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          <span className="text-sm font-semibold">Raw Signal Feed</span>
        </div>
        <span className="text-xs text-slate-500 font-mono">{signals.length} signals</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
        {isLoading && <div className="flex justify-center pt-8"><Spinner /></div>}
        {signals.length === 0 && !isLoading && (
          <div className="text-center py-8 text-slate-500 text-sm">No signals yet. Start the pipeline.</div>
        )}
        {signals.map((s) => (
          <div key={s.signal_id} className="bg-[#0a0b0f] rounded-lg p-2.5 border border-[#1e2130] hover:border-slate-700 transition-colors">
            <div className="flex items-center gap-2 mb-1">
              <SourceBadge source={s.source} />
              {s.ticker && <span className="font-mono text-xs font-bold text-white">${s.ticker}</span>}
              <span className="text-xs text-slate-500 ml-auto font-mono">
                {new Date(s.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="text-xs text-slate-400 line-clamp-2">{s.raw_text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
