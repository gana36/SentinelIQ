import { useState } from 'react'
import { ExternalLink, ChevronDown, ChevronUp, X, Loader2, Play } from 'lucide-react'
import { SentimentBadge } from '../ui/SentimentBadge'
import { ConfidenceBar } from '../ui/ConfidenceBar'
import { SourceBadge } from '../ui/SourceBadge'
import { voiceExplain, markRead, deleteAlert } from '../../api/alerts'
import { draftTrade, executeTrade } from '../../api/trade'
import type { TradeDraft } from '../../api/trade'
import toast from 'react-hot-toast'
import type { Alert, ActionCard as ActionCardType } from '../../types'

interface Props {
  alert?: Alert
  card?: ActionCardType
  compact?: boolean
  onRead?: () => void
  onDelete?: () => void
}

export function ActionCard({ alert, card: cardProp, compact, onRead, onDelete }: Props) {
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

  const handleRead = async () => {
    if (alert?.id) {
      await markRead(alert.id)
      onRead?.()
    }
  }

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (alert?.id) {
      try {
        await deleteAlert(alert.id)
        onDelete?.()
      } catch {
        toast.error('Could not dismiss alert')
      }
    } else {
      onDelete?.()
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
      toast.success(`Trade Sent: ${tradeDraft.action.toUpperCase()} ${tradeDraft.shares} ${tradeDraft.ticker}`)
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
      const res = await voiceExplain(alert.id, 'Narrate current analysis context.')
      setVoiceText(res.data.transcript)
      if (isUnread) handleRead()
    } catch {
      toast.error('Voice unavailable')
    } finally {
      setVoiceLoading(false)
    }
  }

  return (
    <div
      className={`bg-white border transition-all rounded-xl p-6 ${isUnread ? 'border-indigo-400/30 bg-indigo-50/10 shadow-sm' : 'border-slate-200 shadow-sm hover:border-slate-300'}`}
      onClick={isUnread ? handleRead : undefined}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-5">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="font-bold tracking-tighter text-2xl text-slate-900">${card.ticker}</span>
          <SentimentBadge label={card.sentiment?.label ?? 'neutral'} confidence={card.sentiment?.confidence} />
          {isUnread && <span className="text-[9px] font-bold tracking-[0.2em] uppercase text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-sm border border-indigo-100">New Analysis</span>}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {nova.time_horizon && (
            <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase mr-2">{nova.time_horizon}</span>
          )}
          <button onClick={(e) => { e.stopPropagation(); setExpanded(v => !v) }} className="p-1.5 text-slate-400 hover:text-slate-900 transition-colors">
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {(alert?.id || onDelete) && (
            <button onClick={handleDelete} className="p-1.5 text-slate-400 hover:text-red-500 transition-colors" title="Dismiss">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Summary */}
      <p className="text-[15px] font-medium text-slate-700 leading-relaxed mb-6">{card.event_summary}</p>

      {/* Confidence + Credibility */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <ConfidenceBar value={nova.confidence_level ?? 0.5} label="Nova Confidence" />
        <ConfidenceBar value={card.credibility_score ?? 0.5} label="Source Quality" />
      </div>

      {expanded && (
        <>
          {/* Nova Analysis */}
          {nova.primary_driver && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-8 mb-6 pt-6 border-t border-slate-100">
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">Primary Driver</div>
                <p className="text-sm font-semibold text-slate-900 leading-relaxed">{nova.primary_driver}</p>
              </div>
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">Sector Impact</div>
                <p className="text-sm font-semibold text-slate-900 leading-relaxed">{nova.sector_impact}</p>
              </div>
            </div>
          )}

          {/* Risk Factors */}
          {nova.risk_factors?.length > 0 && (
            <div className="mb-6 pt-6 border-t border-slate-100">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-3">Risk Assessment</div>
              <div className="flex flex-wrap gap-2">
                {nova.risk_factors.map((r, i) => (
                  <span key={i} className="text-[11px] font-bold bg-slate-50 border border-slate-200 text-slate-600 px-3 py-1 rounded">{r}</span>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Actions */}
          {nova.recommended_actions?.length > 0 && (
            <div className="mb-6 pt-6 border-t border-slate-100">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-3">Strategic Mandates</div>
              <div className="flex flex-wrap gap-2">
                {nova.recommended_actions.map((a, i) => (
                  <span key={i} className="text-[11px] font-bold bg-slate-900 text-white px-3 py-1 rounded shadow-sm">{a}</span>
                ))}
              </div>
            </div>
          )}

          {/* Similar Historical Events */}
          {card.similar_events?.length > 0 && (
            <div className="mb-6 pt-6 border-t border-slate-100">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-4">Historical Regression</div>
              <div className="space-y-4">
                {card.similar_events.map((ev, i) => (
                  <div key={i} className="flex gap-6 items-start">
                    <div className="w-24 flex-shrink-0 pt-1">
                      <div className="text-[11px] font-bold text-slate-400 tabular-nums uppercase tracking-tighter">{ev.date}</div>
                      <div className="text-[11px] font-bold text-slate-900 mt-0.5">${ev.ticker}</div>
                    </div>
                    <div className="flex-1">
                      <p className="text-[13px] font-semibold text-slate-900 leading-snug">{ev.event}</p>
                      <p className="text-[13px] font-medium text-slate-500 mt-1">Impact: {ev.outcome}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TradingView Chart */}
          {card.chart_screenshot_b64 && (
            <div className="mb-6 pt-6 border-t border-slate-100">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-4">Technical Context</div>
              <div className="rounded-lg overflow-hidden border border-slate-200 bg-slate-50 grayscale-[0.2] contrast-[1.1]">
                <img
                  src={`data:image/png;base64,${card.chart_screenshot_b64}`}
                  alt="Market chart"
                  className="w-full mix-blend-multiply"
                />
              </div>
              {card.chart_analysis && (
                <p className="text-[13px] font-medium text-slate-600 mt-4 border-l-2 border-slate-200 pl-4">{card.chart_analysis}</p>
              )}
            </div>
          )}

          {/* Voice Explanation */}
          {voiceText && (
            <div className="mb-6 bg-slate-50 border border-slate-200 rounded-lg p-5">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-3">Audio Analysis Transcript</div>
              <p className="text-sm font-medium text-slate-900 leading-relaxed italic">{voiceText}</p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <div className="flex items-center gap-4">
              {card.source_links?.[0] && (
                <a href={card.source_links[0]} target="_blank" rel="noopener noreferrer"
                  className="text-[11px] font-bold text-slate-400 hover:text-slate-900 transition-colors uppercase tracking-widest flex items-center gap-1"
                  onClick={e => e.stopPropagation()}>
                  <ExternalLink className="w-2.5 h-2.5" /> Source
                </a>
              )}
              <span className="text-[11px] font-bold font-mono text-slate-400 uppercase">{new Date(card.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={(e) => { e.stopPropagation(); handleDraftTrade('buy') }}
                disabled={tradeLoading}
                className="text-[11px] font-bold px-4 py-1.5 rounded bg-slate-900 text-white hover:bg-slate-800 transition-all uppercase tracking-widest shadow-sm">
                {tradeLoading ? 'Preparing...' : 'Draft Position'}
              </button>
              {alert?.id && (
                <button onClick={(e) => { e.stopPropagation(); handleVoice() }}
                  disabled={voiceLoading}
                  className="p-1.5 text-slate-400 hover:text-slate-900 transition-colors">
                  <Play className={`w-3.5 h-3.5 ${voiceLoading ? 'animate-pulse' : ''}`} />
                </button>
              )}
            </div>
          </div>
        </>
      )}

      {/* Modals: Simple Grayscale aesthetics */}
      {(tradeExecuted || tradeDraft) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-[2px]"
          onClick={() => { setTradeExecuted(null); setTradeDraft(null) }}>
          <div className="bg-white border border-slate-200 rounded-xl p-8 w-full max-w-xl mx-4 shadow-2xl"
            onClick={e => e.stopPropagation()}>
            {tradeExecuted && (
              <>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-xl font-bold tracking-tight text-slate-900">Execution Receipt</h3>
                    <p className="text-xs font-medium text-slate-400 mt-1 uppercase tracking-wider">Automated trade mandate processed</p>
                  </div>
                  <button onClick={() => setTradeExecuted(null)} className="p-1 text-slate-400 hover:text-slate-900"><X className="w-4 h-4" /></button>
                </div>
                <div className="rounded-lg overflow-hidden border border-slate-200 mb-6 bg-slate-50 grayscale">
                  <img src={`data:image/svg+xml;base64,${tradeExecuted.screenshot_b64}`} alt="Receipt" className="w-full" />
                </div>
                <button onClick={() => setTradeExecuted(null)}
                  className="w-full py-3 rounded-lg bg-slate-900 text-white font-bold text-sm uppercase tracking-widest hover:bg-slate-800 transition-all">
                  Close Receipt
                </button>
              </>
            )}
            {tradeDraft && (
              <>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-xl font-bold tracking-tight text-slate-900">Trade Approval</h3>
                    <p className="text-xs font-medium text-slate-400 mt-1 uppercase tracking-wider">Review mandate before final execution</p>
                  </div>
                  <button onClick={() => setTradeDraft(null)} className="p-1 text-slate-400 hover:text-slate-900"><X className="w-4 h-4" /></button>
                </div>
                <div className="rounded-lg overflow-hidden border border-slate-200 mb-6 bg-slate-50 grayscale">
                  <img src={`data:${tradeDraft.screenshot_mime};base64,${tradeDraft.screenshot_b64}`} alt="Draft" className="w-full" />
                </div>
                <div className="grid grid-cols-4 gap-4 mb-8">
                  {[
                    { label: 'Asset', value: `${tradeDraft.ticker}` },
                    { label: 'Type', value: tradeDraft.action.toUpperCase() },
                    { label: 'Volume', value: tradeDraft.shares },
                    { label: 'Value', value: `$${tradeDraft.est_total.toLocaleString()}` },
                  ].map(({ label, value }) => (
                    <div key={label} className="border-b border-slate-100 pb-2">
                      <div className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1">{label}</div>
                      <div className="text-sm font-bold text-slate-900 font-mono">{value}</div>
                    </div>
                  ))}
                </div>
                <div className="flex gap-4">
                  <button onClick={() => setTradeDraft(null)} className="flex-1 py-3 text-sm font-bold text-slate-500 hover:text-slate-900 uppercase tracking-widest transition-colors">Abort</button>
                  <button onClick={handleConfirmTrade} disabled={executeLoading}
                    className="flex-1 py-3 bg-slate-900 text-white font-bold text-sm uppercase tracking-widest rounded-lg hover:bg-slate-800 transition-all shadow-lg flex items-center justify-center gap-2">
                    {executeLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                    Confirm Mandate
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
