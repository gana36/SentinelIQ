export function SourceBadge({ source }: { source: string }) {
  return (
    <span className="text-[9px] font-bold tracking-widest uppercase text-slate-500 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded-sm">
      {source}
    </span>
  )
}
