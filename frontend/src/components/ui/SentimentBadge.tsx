interface Props { label: string; confidence?: number; size?: 'sm' | 'md' }

export function SentimentBadge({ label, confidence, size = 'md' }: Props) {
  const cfg = {
    positive: { cls: 'text-emerald-600' },
    negative: { cls: 'text-red-500' },
    neutral: { cls: 'text-slate-500' },
  }[label] ?? { cls: 'text-slate-500' }

  return (
    <span className={`inline-flex items-center font-bold tracking-wider uppercase ${cfg.cls} ${size === 'sm' ? 'text-[9px]' : 'text-[10px]'}`}>
      <span className="bg-current/10 px-1.5 py-0.5 rounded-sm">{label}</span>
      {confidence !== undefined && (
        <span className="opacity-60 font-medium ml-2 font-mono">{(confidence * 100).toFixed(0)}%</span>
      )}
    </span>
  )
}
