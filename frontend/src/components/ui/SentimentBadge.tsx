import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface Props { label: string; confidence?: number; size?: 'sm' | 'md' }

export function SentimentBadge({ label, confidence, size = 'md' }: Props) {
  const cfg = {
    positive: { cls: 'text-emerald-600', Icon: TrendingUp },
    negative: { cls: 'text-red-500', Icon: TrendingDown },
    neutral: { cls: 'text-slate-500', Icon: Minus },
  }[label] ?? { cls: 'text-slate-500', Icon: Minus }

  return (
    <span className={`inline-flex items-center gap-1 font-medium ${cfg.cls} ${size === 'sm' ? 'text-[11px]' : 'text-xs'}`}>
      <cfg.Icon className="w-3 h-3" />
      <span className="tracking-wide text-[10px] uppercase.">{label}</span>
      {confidence !== undefined && (
        <span className="opacity-70 ml-1">{(confidence * 100).toFixed(0)}%</span>
      )}
    </span>
  )
}
