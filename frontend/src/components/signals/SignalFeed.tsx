import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLiveSignals } from '../../api/market'
import { SourceBadge } from '../ui/SourceBadge'
import { Spinner } from '../ui/Spinner'
import { SignalDetail } from './SignalDetail'
import type { RawSignal } from '../../types'

export function SignalFeed() {
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['live-signals'],
    queryFn: () => getLiveSignals().then(r => r.data),
    refetchInterval: 5000,
  })

  const signals = useMemo(() => data?.signals as RawSignal[] ?? [], [data])

  const { selectedSignal, selectedIndex } = useMemo(() => {
    const index = signals.findIndex(s => s.signal_id === selectedSignalId)
    return {
      selectedSignal: index !== -1 ? signals[index] : null,
      selectedIndex: index
    }
  }, [signals, selectedSignalId])

  const handleNext = () => {
    if (selectedIndex < signals.length - 1) {
      setSelectedSignalId(signals[selectedIndex + 1].signal_id)
    }
  }

  const handlePrev = () => {
    if (selectedIndex > 0) {
      setSelectedSignalId(signals[selectedIndex - 1].signal_id)
    }
  }

  return (
    <div className="card h-full flex flex-col p-0 overflow-hidden relative">
      <div className="flex items-center justify-between p-4 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-bold tracking-tight text-slate-800 uppercase">Intelligence Feed</span>
        </div>
        <span className="text-[10px] font-bold text-slate-400 tabular-nums uppercase tracking-wider">{signals.length} Entries</span>
      </div>
      <div className="flex-1 overflow-y-auto min-h-0">
        {isLoading && <div className="flex justify-center pt-8"><Spinner /></div>}
        {signals.length === 0 && !isLoading && (
          <div className="text-center py-12 text-slate-400 text-xs font-medium italic">Monitoring for live signals...</div>
        )}
        <div className="divide-y divide-slate-100">
          {signals.map((s) => (
            <div
              key={s.signal_id}
              onClick={() => setSelectedSignalId(s.signal_id)}
              className={`px-4 py-2.5 cursor-pointer transition-all border-l-2 ${selectedSignalId === s.signal_id
                ? 'bg-slate-50 border-slate-900'
                : 'border-transparent hover:bg-slate-50/50'
                }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <SourceBadge source={s.source} />
                {s.ticker && (
                  <span className="font-bold text-[12px] text-slate-900 leading-none">
                    ${s.ticker}
                  </span>
                )}
                <span className="text-[10px] text-slate-400 font-medium tabular-nums ml-auto tracking-tighter">
                  {new Date(s.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              </div>
              <p className="text-[12px] text-slate-600 leading-[1.4] font-medium line-clamp-2 pr-2">
                {s.raw_text}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Detail Panel */}
      {selectedSignal && (
        <SignalDetail
          signal={selectedSignal}
          onClose={() => setSelectedSignalId(null)}
          hasNext={selectedIndex < signals.length - 1}
          hasPrev={selectedIndex > 0}
          onNext={handleNext}
          onPrev={handlePrev}
        />
      )}
    </div>
  )
}
