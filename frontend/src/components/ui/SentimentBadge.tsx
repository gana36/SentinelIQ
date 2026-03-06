import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface Props { label: string; confidence?: number; size?: 'sm' | 'md' }

export function SentimentBadge({ label, confidence, size = 'md' }: Props) {
  const cfg = {
    positive: { cls: 'badge-positive', Icon: TrendingUp },
    negative: { cls: 'badge-negative', Icon: TrendingDown },
    neutral:  { cls: 'badge-neutral', Icon: Minus },
  }[label] ?? { cls: 'badge-neutral', Icon: Minus }

  return (
    <span className={`inline-flex items-center gap-1 ${cfg.cls} ${size === 'sm' ? 'text-xs' : 'text-sm'}`}>
      <cfg.Icon className="w-3 h-3" />
      {label.toUpperCase()}
      {confidence !== undefined && (
        <span className="opacity-70 ml-1">{(confidence * 100).toFixed(0)}%</span>
      )}
    </span>
  )
}
