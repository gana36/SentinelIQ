import { useState } from 'react'
import { Shield, TrendingUp, Clock, AlertTriangle, Mic, ExternalLink, ChevronDown, ChevronUp, History, ShoppingCart, X, Loader2 } from 'lucide-react'
import { SentimentBadge } from '../ui/SentimentBadge'
import { ConfidenceBar } from '../ui/ConfidenceBar'
import { SourceBadge } from '../ui/SourceBadge'
import { voiceExplain, markRead } from '../../api/alerts'
import { draftTrade, executeTrade } from '../../api/trade'
import type { TradeDraft } from '../../api/trade'
import toast from 'react-hot-toast'
import type { Alert, ActionCard as ActionCardType } from '../../types'

interface Props {
  alert?: Alert
  card?: ActionCardType
  compact?: boolean
  onRead?: () => void
}

export function ActionCard({ alert, card: cardProp, compact, onRead }: Props) {
  const card = cardProp ?? alert?.payload
  if (!card) return null

  const [expanded, setExpanded] = useState(!compact)
  const [voiceLoading, setVoiceLoading] = useState(false)
  const [voiceText, setVoiceText] = useState<string | null>(null)
  const [tradeLoading, setTradeLoading] = useState(false)
  const [executeLoading, setExecuteLoading] = useState(false)
  const [tradeDraft, setTradeDraft] = useState<TradeDraft | null>(null)
  const [tradeExecuted, setTradeExecuted] = useState<TradeDraft | null>(null)

  const nova = card.nova_analysis ?? {}
  const isUnread = alert && !alert.read_at
  const timeHorizonColor = { intraday: 'text-yellow-400', 'short-term': 'text-blue-400', 'long-term': 'text-purple-400' }[nova.time_horizon ?? 'intraday']

  const handleRead = async () => {
    if (alert?.id) {
      await markRead(alert.id)
      onRead?.()
    }
  }

  const handleDraftTrade = async (action: 'buy' | 'sell') => {
    setTradeLoading(true)
    try {
      const res = await draftTrade({
        ticker: card.ticker,
        action,
        shares: 1,
        est_price: card.nova_analysis?.confidence_level ? card.nova_analysis.confidence_level * 1000 : 100,
      })
      setTradeDraft(res.data)
    } catch {
      toast.error('Nova Act could not prepare trade draft')
    } finally {
      setTradeLoading(false)
    }
  }

  const handleConfirmTrade = async () => {
    if (!tradeDraft) return
    setExecuteLoading(true)
    try {
      const res = await executeTrade({
        ticker: tradeDraft.ticker,
        action: tradeDraft.action,
        shares: tradeDraft.shares,
        est_price: tradeDraft.est_price,
      })
      setTradeDraft(null)
      setTradeExecuted(res.data)
      toast.success(`Nova Act executed: ${tradeDraft.action.toUpperCase()} ${tradeDraft.shares} ${tradeDraft.ticker} — confirmation email sent!`)
    } catch {
      toast.error('Nova Act could not execute the trade')
    } finally {
      setExecuteLoading(false)
    }
  }

  const handleVoice = async () => {
    if (!alert?.id) return
    setVoiceLoading(true)
    try {
      const res = await voiceExplain(alert.id, 'Why is this stock moving and what should I watch for?')
      setVoiceText(res.data.transcript)
      if (isUnread) handleRead()
    } catch {
      toast.error('Voice explanation unavailable')
    } finally {
      setVoiceLoading(false)
    }
  }

  return (
    <div
      className={`card transition-all hover:border-slate-700 ${isUnread ? 'border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.05)]' : ''}`}
      onClick={isUnread ? handleRead : undefined}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono font-bold text-xl text-white">${card.ticker}</span>
          <SentimentBadge label={card.sentiment?.label ?? 'neutral'} confidence={card.sentiment?.confidence} />
          {isUnread && <span className="text-xs bg-emerald-500 text-black px-2 py-0.5 rounded-full font-bold">NEW</span>}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {nova.time_horizon && (
            <span className={`text-xs font-mono ${timeHorizonColor}`}>{nova.time_horizon.toUpperCase()}</span>
          )}
          <button onClick={(e) => { e.stopPropagation(); setExpanded(v => !v) }} className="btn-ghost p-1">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Summary */}
      <p className="text-sm text-slate-300 leading-relaxed mb-3">{card.event_summary}</p>

      {/* Confidence + Credibility */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <ConfidenceBar value={nova.confidence_level ?? 0.5} label="Nova Confidence" />
        <ConfidenceBar value={card.credibility_score ?? 0.5} label="Source Credibility" />
      </div>

      {expanded && (
        <>
          {/* Nova Analysis */}
          {nova.primary_driver && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
              <div className="bg-[#0a0b0f] rounded-lg p-3">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1"><TrendingUp className="w-3 h-3" />PRIMARY DRIVER</div>
                <p className="text-sm text-slate-300">{nova.primary_driver}</p>
              </div>
              <div className="bg-[#0a0b0f] rounded-lg p-3">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1"><Shield className="w-3 h-3" />SECTOR IMPACT</div>
                <p className="text-sm text-slate-300">{nova.sector_impact}</p>
              </div>
            </div>
          )}

          {/* Risk Factors */}
          {nova.risk_factors?.length > 0 && (
            <div className="mb-3">
              <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-2"><AlertTriangle className="w-3 h-3" />RISK FACTORS</div>
              <div className="flex flex-wrap gap-1.5">
                {nova.risk_factors.map((r, i) => (
                  <span key={i} className="text-xs bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded-full">{r}</span>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Actions */}
          {nova.recommended_actions?.length > 0 && (
            <div className="mb-3">
              <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-2"><Clock className="w-3 h-3" />RECOMMENDED ACTIONS</div>
              <div className="flex flex-wrap gap-1.5">
                {nova.recommended_actions.map((a, i) => (
                  <span key={i} className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">{a}</span>
                ))}
              </div>
            </div>
          )}

          {/* Similar Historical Events */}
          {card.similar_events?.length > 0 && (
            <div className="mb-3">
              <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-2"><History className="w-3 h-3" />SIMILAR HISTORICAL EVENTS</div>
              <div className="space-y-2">
                {card.similar_events.map((ev, i) => (
                  <div key={i} className="bg-[#0a0b0f] rounded-lg p-2.5 flex gap-3">
                    <div className="flex-shrink-0 text-right">
                      <div className="font-mono text-xs text-slate-500">{ev.date}</div>
                      <div className="font-mono text-xs font-bold text-slate-300">{ev.ticker}</div>
                      <div className="text-xs text-emerald-400">{(ev.similarity_score * 100).toFixed(0)}% match</div>
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs text-slate-300 line-clamp-2">{ev.event}</p>
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">→ {ev.outcome}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TradingView Chart (Nova Act screenshot + Nova multimodal analysis) */}
          {card.chart_screenshot_b64 && (
            <div className="mb-3">
              <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-2">
                <TrendingUp className="w-3 h-3" />TRADINGVIEW CHART
              </div>
              <div className="rounded-lg overflow-hidden border border-[#1e2130]">
                <img
                  src={`data:image/png;base64,${card.chart_screenshot_b64}`}
                  alt={`${card.ticker} chart`}
                  className="w-full"
                />
              </div>
              {card.chart_analysis && (
                <p className="text-xs text-slate-400 mt-2 leading-relaxed">{card.chart_analysis}</p>
              )}
            </div>
          )}

          {/* Voice Explanation */}
          {voiceText && (
            <div className="mb-3 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
              <div className="flex items-center gap-1.5 text-xs text-blue-400 mb-2"><Mic className="w-3 h-3" />NOVA SONIC EXPLANATION</div>
              <p className="text-sm text-slate-300 italic">"{voiceText}"</p>
            </div>
          )}

          {/* Footer: source links + actions */}
          <div className="flex items-center justify-between pt-2 border-t border-[#1e2130]">
            <div className="flex items-center gap-2">
              {card.source_links?.[0] && (
                <a href={card.source_links[0]} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                  onClick={e => e.stopPropagation()}>
                  <ExternalLink className="w-3 h-3" />Source
                </a>
              )}
              <span className="text-xs text-slate-600">{new Date(card.timestamp).toLocaleTimeString()}</span>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={(e) => { e.stopPropagation(); handleDraftTrade('buy') }}
                disabled={tradeLoading}
                className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors">
                {tradeLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <ShoppingCart className="w-3 h-3" />}
                Draft Trade
              </button>
              {alert?.id && (
                <button onClick={(e) => { e.stopPropagation(); handleVoice() }}
                  disabled={voiceLoading}
                  className="flex items-center gap-1.5 text-xs btn-ghost py-1">
                  <Mic className={`w-3.5 h-3.5 ${voiceLoading ? 'animate-pulse text-blue-400' : ''}`} />
                  {voiceLoading ? 'Explaining...' : 'Ask Nova'}
                </button>
              )}
            </div>
          </div>
        </>
      )}

      {/* Trade Executed Modal */}
      {tradeExecuted && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setTradeExecuted(null)}>
          <div className="bg-[#111318] border border-emerald-500/30 rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl"
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-white text-lg">Trade Executed ✓</h3>
                <p className="text-xs text-slate-500 mt-0.5">Nova Act submitted your paper trade{tradeExecuted.is_mock ? ' (mock)' : ''}. Confirmation email sent.</p>
              </div>
              <button onClick={() => setTradeExecuted(null)} className="btn-ghost p-1.5"><X className="w-4 h-4" /></button>
            </div>
            <div className="rounded-xl overflow-hidden border border-[#1e2130] mb-4 bg-[#0a0b0f]">
              <img
                src={`data:image/svg+xml;base64,${tradeExecuted.screenshot_b64}`}
                alt="Nova Act execution screenshot"
                className="w-full"
              />
            </div>
            <button onClick={() => setTradeExecuted(null)}
              className="w-full py-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors text-sm font-semibold">
              Done
            </button>
          </div>
        </div>
      )}

      {/* Trade Draft Modal */}
      {tradeDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setTradeDraft(null)}>
          <div className="bg-[#111318] border border-[#1e2130] rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl"
            onClick={e => e.stopPropagation()}>
            {/* Modal header */}
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-white text-lg">Nova Act — Trade Draft</h3>
                <p className="text-xs text-slate-500 mt-0.5">Review before confirming. No real money involved{tradeDraft.is_mock ? ' (mock)' : ' (paper trading)'}.</p>
              </div>
              <button onClick={() => setTradeDraft(null)} className="btn-ghost p-1.5">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Screenshot */}
            <div className="rounded-xl overflow-hidden border border-[#1e2130] mb-4 bg-[#0a0b0f]">
              <img
                src={`data:${tradeDraft.screenshot_mime};base64,${tradeDraft.screenshot_b64}`}
                alt="Nova Act trade form screenshot"
                className="w-full"
              />
            </div>

            {/* Order summary */}
            <div className="grid grid-cols-4 gap-3 mb-5 text-center">
              {[
                { label: 'Ticker', value: `$${tradeDraft.ticker}` },
                { label: 'Action', value: tradeDraft.action.toUpperCase(), color: tradeDraft.action === 'buy' ? 'text-emerald-400' : 'text-red-400' },
                { label: 'Shares', value: tradeDraft.shares },
                { label: 'Est. Total', value: `$${tradeDraft.est_total.toLocaleString()}` },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-[#0a0b0f] rounded-lg p-2">
                  <div className="text-xs text-slate-500 mb-1">{label}</div>
                  <div className={`text-sm font-bold font-mono ${color ?? 'text-white'}`}>{value}</div>
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button onClick={() => setTradeDraft(null)}
                className="flex-1 py-2.5 rounded-xl border border-[#1e2130] text-slate-400 hover:text-white hover:border-slate-600 transition-colors text-sm">
                Cancel
              </button>
              <button
                onClick={handleConfirmTrade}
                disabled={executeLoading}
                className={`flex-1 py-2.5 rounded-xl font-semibold text-sm transition-colors flex items-center justify-center gap-2 ${tradeDraft.action === 'buy' ? 'bg-emerald-500 hover:bg-emerald-400 text-black' : 'bg-red-500 hover:bg-red-400 text-white'}`}>
                {executeLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {executeLoading ? 'Nova Act executing...' : `Confirm ${tradeDraft.action.toUpperCase()}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
