import { useEffect, useState, useMemo } from 'react'
import { X, ChevronLeft, ChevronRight, Copy, ExternalLink, Hash, Clock, Globe, Shield, User, Terminal, FileCode, ChevronDown, ChevronUp, Twitter } from 'lucide-react'
import type { RawSignal } from '../../types'
import { SourceBadge } from '../ui/SourceBadge'
import toast from 'react-hot-toast'

interface Props {
    signal: RawSignal
    onClose: () => void
    onNext?: () => void
    onPrev?: () => void
    hasNext: boolean
    hasPrev: boolean
}

export function SignalDetail({ signal, onClose, onNext, onPrev, hasNext, hasPrev }: Props) {
    const [showTechnical, setShowTechnical] = useState(false)
    const [showRaw, setShowRaw] = useState(false)

    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose()
        }
        window.addEventListener('keydown', handleEsc)
        return () => window.removeEventListener('keydown', handleEsc)
    }, [onClose])

    const handleCopy = () => {
        navigator.clipboard.writeText(signal.raw_text)
        toast.success('Text copied to clipboard')
    }

    // Safely extract potential metadata
    const url = (signal.metadata?.url as string) || (signal.metadata?.link as string)
    const sourceType = (signal.metadata?.source_type as string) || 'Raw Feed'
    const author = (signal.metadata?.author as string) || ((signal.metadata?.user as any)?.name as string) || (signal.metadata?.username as string) || 'Secondary Intelligence Source'
    const handle = (signal.metadata?.user as any)?.screen_name || signal.metadata?.username || signal.metadata?.handle || 'source_id'
    const entities = signal.metadata?.entities as string[] | undefined
    const isTwitter = signal.source?.toLowerCase() === 'twitter' || signal.source?.toLowerCase() === 'x'

    // Text normalization logic
    const formattedContent = useMemo(() => {
        if (!signal.raw_text) return null

        const parts = signal.raw_text.split(/(\$[A-Z]+|#[a-zA-Z0-9_]+|@[a-zA-Z0-9_]+)/g)
        return parts.map((part, i) => {
            if (part.startsWith('$')) {
                return <span key={i} className="text-slate-900 font-bold bg-slate-100/50 px-1 rounded">{part}</span>
            }
            if (part.startsWith('#')) {
                return <span key={i} className="text-slate-500 font-semibold">{part}</span>
            }
            if (part.startsWith('@')) {
                return <span key={i} className="text-indigo-500/80 font-medium">{part}</span>
            }
            return part
        })
    }, [signal.raw_text])

    return (
        <div className="fixed inset-y-0 right-0 w-full max-w-xl bg-white shadow-2xl z-50 flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-300">
            {/* Navigation Header */}
            <div className="flex items-center justify-between px-6 py-3 border-b border-slate-100 bg-white">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1 border border-slate-200 rounded-lg p-0.5">
                        <button
                            onClick={onPrev}
                            disabled={!hasPrev}
                            className="p-1 text-slate-400 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-30 disabled:hover:bg-transparent transition-all rounded"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </button>
                        <button
                            onClick={onNext}
                            disabled={!hasNext}
                            className="p-1 text-slate-400 hover:text-slate-900 hover:bg-slate-50 disabled:opacity-30 disabled:hover:bg-transparent transition-all rounded"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                    <div className="h-4 w-px bg-slate-200 mx-1" />
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Inspection Panel</span>
                </div>
                <button
                    onClick={onClose}
                    className="p-1.5 text-slate-400 hover:text-slate-900 hover:bg-slate-50 rounded-lg transition-all"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto">
                <div className="p-8 max-w-lg mx-auto space-y-10">
                    {/* Enhanced Metadata Header */}
                    <div className="space-y-6">
                        <div className="flex items-center gap-3">
                            <SourceBadge source={signal.source} />
                            {signal.ticker && (
                                <span className="text-xl font-bold tracking-tight text-slate-900">
                                    ${signal.ticker}
                                </span>
                            )}
                            <span className="text-[9px] font-mono text-slate-300 ml-auto uppercase tracking-tighter">ID: {signal.signal_id.slice(0, 8)}...</span>
                        </div>

                        <div className="grid grid-cols-2 gap-y-4 gap-x-8 pb-6 border-b border-slate-100">
                            <div className="space-y-1">
                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                    <Globe className="w-3 h-3" />
                                    Source type
                                </div>
                                <div className="text-[13px] font-semibold text-slate-800">{sourceType}</div>
                            </div>
                            <div className="space-y-1">
                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                    <Clock className="w-3 h-3" />
                                    Received
                                </div>
                                <div className="text-[13px] font-semibold text-slate-800 tabular-nums">
                                    {new Date(signal.timestamp).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                                </div>
                            </div>
                            {author && (
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                        <User className="w-3 h-3" />
                                        Origin
                                    </div>
                                    <div className="text-[13px] font-semibold text-slate-800">{author}</div>
                                </div>
                            )}
                            <div className="space-y-1">
                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                    <Shield className="w-3 h-3" />
                                    Classification
                                </div>
                                <div className="text-[13px] font-semibold text-slate-800">Raw Intelligence</div>
                            </div>
                        </div>
                    </div>

                    {/* Premium Evidence Section */}
                    <div className="space-y-4">
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Signal Evidence</div>

                        {isTwitter ? (
                            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4 relative overflow-hidden group hover:border-slate-300 transition-all">
                                <div className="absolute top-0 right-0 p-4 opacity-[0.03] scale-[4] origin-top-right group-hover:scale-[4.5] transition-transform duration-500">
                                    <Twitter className="w-8 h-8" />
                                </div>
                                <div className="flex items-center gap-3 relative z-10">
                                    <div className="w-10 h-10 bg-slate-50 rounded-full flex items-center justify-center border border-slate-100 overflow-hidden shadow-inner">
                                        <User className="w-5 h-5 text-slate-300" />
                                    </div>
                                    <div>
                                        <div className="text-[14px] font-bold text-slate-900 leading-tight">{author}</div>
                                        <div className="text-[12px] text-slate-400 font-medium">@{handle}</div>
                                    </div>
                                    <div className="ml-auto">
                                        <Twitter className="w-4 h-4 text-[#1da1f2] opacity-80" />
                                    </div>
                                </div>
                                <div className="relative z-10">
                                    <p className="text-[17px] text-slate-800 leading-[1.6] font-medium whitespace-pre-wrap tracking-tight">
                                        {formattedContent}
                                    </p>
                                </div>
                                <div className="pt-4 border-t border-slate-50 flex items-center justify-between text-[11px] font-medium text-slate-400 tabular-nums relative z-10">
                                    <div>
                                        {new Date(signal.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {new Date(signal.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                                    </div>
                                    <div className="flex items-center gap-1 text-slate-300">
                                        <Globe className="w-3 h-3" />
                                        <span>Public Data</span>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="bg-slate-50/50 border border-slate-100 rounded-xl p-6">
                                <p className="text-[16px] text-slate-800 leading-[1.8] font-medium whitespace-pre-wrap tracking-tight">
                                    {formattedContent}
                                </p>
                            </div>
                        )}

                        {url && (
                            <div className="pt-2">
                                <a
                                    href={url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center gap-1.5 text-[11px] font-bold text-indigo-600 hover:text-indigo-800 transition-colors uppercase tracking-widest"
                                >
                                    <ExternalLink className="w-3 h-3" />
                                    Inspect External Reference
                                </a>
                            </div>
                        )}
                    </div>

                    {/* Entities - subtle metadata Area */}
                    {entities && entities.length > 0 && (
                        <div className="space-y-3">
                            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Extracted Identifiers</div>
                            <div className="flex flex-wrap gap-1.5">
                                {entities.map((ent, i) => (
                                    <span key={i} className="px-2 py-0.5 bg-slate-50 border border-slate-100 rounded text-[11px] font-bold text-slate-500 flex items-center gap-1">
                                        <Hash className="w-2.5 h-2.5 opacity-50" />
                                        {ent}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Technical Disclosure */}
                    <div className="border-t border-slate-100 pt-6 space-y-4">
                        <button
                            onClick={() => setShowTechnical(!showTechnical)}
                            className="flex items-center justify-between w-full text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] hover:text-slate-600 transition-colors"
                        >
                            <span className="flex items-center gap-2">
                                <Terminal className="w-3 h-3" />
                                System Attributes
                            </span>
                            {showTechnical ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>

                        {showTechnical && (
                            <div className="bg-slate-50/50 rounded-lg p-4 grid grid-cols-2 gap-4">
                                {Object.entries(signal.metadata || {}).map(([key, value]) => {
                                    if (['url', 'link', 'entities', 'source_type', 'author', 'user', 'username', 'screen_name', 'handle'].includes(key)) return null
                                    if (typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean') return null
                                    return (
                                        <div key={key}>
                                            <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">{key.replace(/_/g, ' ')}</div>
                                            <div className="text-xs font-mono text-slate-600 break-all">{String(value)}</div>
                                        </div>
                                    )
                                })}
                                <div className="col-span-2">
                                    <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest mb-1">Internal Reference</div>
                                    <div className="text-xs font-mono text-slate-600 select-all">{signal.signal_id}</div>
                                </div>
                            </div>
                        )}

                        <button
                            onClick={() => setShowRaw(!showRaw)}
                            className="flex items-center justify-between w-full text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] hover:text-slate-600 transition-colors"
                        >
                            <span className="flex items-center gap-2">
                                <FileCode className="w-3 h-3" />
                                Raw source dump
                            </span>
                            {showRaw ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>

                        {showRaw && (
                            <div className="bg-slate-900 rounded-lg p-4">
                                <pre className="text-[11px] text-slate-400 font-mono whitespace-pre-wrap leading-relaxed overflow-x-auto">
                                    {signal.raw_text}
                                </pre>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Footer Actions */}
            <div className="px-8 py-5 border-t border-slate-100 flex items-center justify-between bg-white">
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleCopy}
                        className="px-4 py-2 border border-slate-200 text-slate-600 text-[11px] font-bold uppercase tracking-widest rounded-lg hover:bg-slate-50 hover:border-slate-300 transition-all flex items-center gap-2"
                    >
                        <Copy className="w-3.5 h-3.5" />
                        Copy evidence
                    </button>
                </div>
                {url && (
                    <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-4 py-2 bg-slate-900 text-white text-[11px] font-bold uppercase tracking-widest rounded-lg shadow-sm hover:bg-slate-800 transition-all flex items-center gap-2"
                    >
                        <ExternalLink className="w-3.5 h-3.5" />
                        Open Source
                    </a>
                )}
            </div>
        </div>
    )
}
