import { useState } from 'react'
import { Shield, TrendingUp, Clock, AlertTriangle, Mic, ExternalLink, ChevronDown, ChevronUp, History } from 'lucide-react'
import { SentimentBadge } from '../ui/SentimentBadge'
import { ConfidenceBar } from '../ui/ConfidenceBar'
import { SourceBadge } from '../ui/SourceBadge'
import { voiceExplain } from '../../api/alerts'
import { markRead } from '../../api/alerts'
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

  const nova = card.nova_analysis ?? {}
  const isUnread = alert && !alert.read_at
  const timeHorizonColor = { intraday: 'text-yellow-400', 'short-term': 'text-blue-400', 'long-term': 'text-purple-400' }[nova.time_horizon ?? 'intraday']

  const handleRead = async () => {
    if (alert?.id) {
      await markRead(alert.id)
      onRead?.()
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
            {alert?.id && (
              <button onClick={(e) => { e.stopPropagation(); handleVoice() }}
                disabled={voiceLoading}
                className="flex items-center gap-1.5 text-xs btn-ghost py-1">
                <Mic className={`w-3.5 h-3.5 ${voiceLoading ? 'animate-pulse text-blue-400' : ''}`} />
                {voiceLoading ? 'Explaining...' : 'Ask Nova'}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}
