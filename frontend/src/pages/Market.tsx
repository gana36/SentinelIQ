import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart2, Search, ExternalLink, RefreshCw } from 'lucide-react'
import { getQuote, getNews } from '../api/market'
import { ConfidenceBar } from '../components/ui/ConfidenceBar'
import { Spinner } from '../components/ui/Spinner'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export function Market() {
  const [ticker, setTicker] = useState('TSLA')
  const [search, setSearch] = useState('TSLA')

  const { data: quote, isLoading: quoteLoading, refetch } = useQuery({
    queryKey: ['quote', ticker],
    queryFn: () => getQuote(ticker).then(r => r.data),
    refetchInterval: 30_000,
  })

  const { data: news, isLoading: newsLoading } = useQuery({
    queryKey: ['news', ticker],
    queryFn: () => getNews(ticker).then(r => r.data),
    refetchInterval: 60_000,
  })

  // Mock mini chart data (replace with real historical in production)
  const mockChartData = Array.from({ length: 20 }, (_, i) => ({
    t: `${i}m`, price: (quote?.price ?? 100) + (Math.sin(i * 0.5) * 5) + (Math.random() * 2 - 1)
  }))

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-2">
        <BarChart2 className="w-5 h-5 text-emerald-400" />
        <h1 className="text-2xl font-semibold tracking-tight text-content-primary">Market</h1>
      </div>

      <form onSubmit={e => { e.preventDefault(); setTicker(search.toUpperCase()) }} className="flex gap-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input className="input pl-9 max-w-xs font-mono uppercase" placeholder="Search ticker..."
            value={search} onChange={e => setSearch(e.target.value.toUpperCase())} />
        </div>
        <button type="submit" className="btn-primary">Lookup</button>
        <button type="button" onClick={() => refetch()} className="btn-ghost"><RefreshCw className="w-4 h-4" /></button>
      </form>

      {quoteLoading && <Spinner size="lg" />}

      {quote && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Quote card */}
          <div className="card space-y-4">
            <div>
              <div className="text-sm font-medium text-content-secondary mb-0.5">Current Price</div>
              <div className="text-4xl font-mono font-semibold tracking-tight text-content-primary">${quote.price.toFixed(2)}</div>
              <div className={`text-sm font-mono mt-1 ${quote.change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {quote.change_pct >= 0 ? '+' : ''}{quote.change_pct.toFixed(2)}% today
              </div>
            </div>
            <div className="space-y-3 pt-2 border-t border-border">
              <div>
                <div className="text-sm font-medium text-content-secondary mb-1">Volume: {quote.volume.toLocaleString()}</div>
                <ConfidenceBar value={Math.min(Math.abs(quote.volume_zscore) / 4, 1)} label="Volume Anomaly Score" />
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-app rounded p-2">
                  <div className="text-sm font-medium text-content-secondary">Vol Z-Score</div>
                  <div className={`font-mono font-semibold tracking-tight mt-0.5 ${Math.abs(quote.volume_zscore) > 2 ? 'text-yellow-400' : 'text-slate-300'}`}>
                    {quote.volume_zscore.toFixed(2)}σ
                  </div>
                </div>
                <div className="bg-app rounded p-2">
                  <div className="text-sm font-medium text-content-secondary">Ticker</div>
                  <div className="font-mono font-semibold tracking-tight mt-0.5 text-emerald-400">${quote.ticker}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Mini chart */}
          <div className="lg:col-span-2 card">
            <div className="text-sm font-medium text-content-secondary mb-3">Price (Simulated)</div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={mockChartData}>
                <defs>
                  <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="t" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
                <Tooltip contentStyle={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12, boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}
                  itemStyle={{ color: '#10b981' }} labelStyle={{ color: '#64748b' }} />
                <Area type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2} fill="url(#priceGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* News */}
      <div>
        <h2 className="text-base font-medium text-content-primary mb-3">Latest News</h2>
        {newsLoading && <Spinner />}
        <div className="space-y-2">
          {(news ?? []).map((item, i) => (
            <a key={i} href={item.url} target="_blank" rel="noopener noreferrer"
              className="card flex items-start gap-3 hover:border-slate-300 transition-colors group no-underline">
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-800 group-hover:text-slate-900 transition-colors line-clamp-2 font-medium">{item.title}</p>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-xs text-slate-500">{item.source}</span>
                  <span className="text-xs text-slate-400">{item.published_at ? new Date(item.published_at).toLocaleDateString() : ''}</span>
                </div>
              </div>
              <ExternalLink className="w-4 h-4 text-slate-400 group-hover:text-slate-600 flex-shrink-0 mt-0.5 transition-colors" />
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
