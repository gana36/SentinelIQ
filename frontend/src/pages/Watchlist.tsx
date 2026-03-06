import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Star, Plus, Trash2, RefreshCw } from 'lucide-react'
import { getWatchlist, addTicker, removeTicker } from '../api/watchlist'
import { getQuote } from '../api/market'
import { Spinner } from '../components/ui/Spinner'
import toast from 'react-hot-toast'

function TickerRow({ ticker, onRemove }: { ticker: string; onRemove: () => void }) {
  const { data } = useQuery({
    queryKey: ['quote', ticker],
    queryFn: () => getQuote(ticker).then(r => r.data),
    refetchInterval: 30_000,
  })
  const changeColor = (data?.change_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'

  return (
    <div className="card flex items-center justify-between hover:border-slate-700 transition-colors">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 bg-emerald-500/10 rounded-lg flex items-center justify-center">
          <span className="font-mono font-bold text-emerald-400 text-sm">{ticker[0]}</span>
        </div>
        <div>
          <div className="font-mono font-bold">${ticker}</div>
          {data && <div className="text-xs text-slate-500">Vol: {data.volume.toLocaleString()}</div>}
        </div>
      </div>
      <div className="flex items-center gap-6">
        {data && (
          <>
            <div className="text-right">
              <div className="font-mono font-semibold">${data.price.toFixed(2)}</div>
              <div className={`text-xs font-mono ${changeColor}`}>
                {data.change_pct >= 0 ? '+' : ''}{data.change_pct.toFixed(2)}%
              </div>
            </div>
            <div className="text-right hidden sm:block">
              <div className="text-xs text-slate-500">Vol Z-Score</div>
              <div className={`text-xs font-mono ${Math.abs(data.volume_zscore) > 2 ? 'text-yellow-400' : 'text-slate-400'}`}>
                {data.volume_zscore.toFixed(2)}σ
              </div>
            </div>
          </>
        )}
        <button onClick={onRemove} className="btn-ghost text-red-500/60 hover:text-red-400 p-1">
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

export function Watchlist() {
  const [input, setInput] = useState('')
  const qc = useQueryClient()

  const { data: items, isLoading } = useQuery({ queryKey: ['watchlist'], queryFn: () => getWatchlist().then(r => r.data) })

  const add = useMutation({
    mutationFn: (t: string) => addTicker(t),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['watchlist'] }); setInput(''); toast.success('Ticker added') },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Failed to add'),
  })

  const remove = useMutation({
    mutationFn: removeTicker,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['watchlist'] }); toast.success('Removed') },
  })

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) add.mutate(input.trim().toUpperCase())
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2">
        <Star className="w-5 h-5 text-emerald-400" />
        <h1 className="text-2xl font-bold">Watchlist</h1>
        <span className="text-sm text-slate-400 ml-1">({items?.length ?? 0} tickers)</span>
      </div>

      <form onSubmit={handleAdd} className="flex gap-2">
        <input className="input max-w-xs font-mono uppercase" placeholder="Add ticker... (e.g. AAPL)"
          value={input} onChange={e => setInput(e.target.value.toUpperCase())} />
        <button type="submit" disabled={add.isPending || !input.trim()} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />{add.isPending ? 'Adding...' : 'Add'}
        </button>
      </form>

      {isLoading && <div className="flex justify-center py-12"><Spinner size="lg" /></div>}

      {!isLoading && (items?.length ?? 0) === 0 && (
        <div className="card text-center py-16 text-slate-500">
          <Star className="w-10 h-10 mx-auto mb-3 opacity-20" />
          <p>Your watchlist is empty</p>
          <p className="text-xs mt-1">Add tickers to receive real-time alerts</p>
        </div>
      )}

      <div className="space-y-3">
        {items?.map(item => (
          <TickerRow key={item.id} ticker={item.ticker} onRemove={() => remove.mutate(item.ticker)} />
        ))}
      </div>
    </div>
  )
}
