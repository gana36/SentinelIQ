interface Props { value: number; label?: string }

export function ConfidenceBar({ value, label }: Props) {
  const pct = Math.round(value * 100)
  const color = pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'
  return (
    <div className="w-full">
      {label && <div className="flex justify-between text-[10px] uppercase tracking-wide font-medium text-slate-500 mb-1.5"><span>{label}</span><span>{pct}%</span></div>}
      <div className="h-1 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
