export function SourceBadge({ source }: { source: string }) {
  return (
    <span className="text-[10px] font-bold tracking-tight uppercase text-slate-400 bg-slate-50/50 px-1.5 py-0.5 rounded border border-slate-100">
      {source}
    </span>
  )
}
