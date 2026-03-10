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
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <span className="text-[15px] font-semibold tracking-tight text-slate-900">Raw Signal Feed</span>
        </div>
        <span className="text-xs font-medium text-slate-400">{signals.length} signals</span>
      </div>
      <div className="flex-1 overflow-y-auto min-h-0">
        {isLoading && <div className="flex justify-center pt-8"><Spinner /></div>}
        {signals.length === 0 && !isLoading && (
          <div className="text-center py-8 text-slate-500 text-sm">No signals yet. Start the pipeline.</div>
        )}
        <div className="divide-y divide-slate-100">
          {signals.map((s) => (
            <div key={s.signal_id} className="py-3 group pr-1">
              <div className="flex items-center gap-2.5 mb-1.5">
                <SourceBadge source={s.source} />
                {s.ticker && <span className="font-semibold text-[13px] text-slate-900 leading-none mt-0.5">${s.ticker}</span>}
                <span className="text-[10px] text-slate-400 font-mono ml-auto mt-0.5 whitespace-nowrap">
                  {new Date(s.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>
              <p className="text-[13px] text-slate-600 leading-snug line-clamp-2">{s.raw_text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
