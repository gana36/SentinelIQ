const COLORS: Record<string, string> = {
  reddit: 'bg-orange-500/15 text-orange-400 border-orange-500/20',
  news: 'bg-blue-500/15 text-blue-400 border-blue-500/20',
  market: 'bg-purple-500/15 text-purple-400 border-purple-500/20',
  sec: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/20',
  mock: 'bg-slate-500/15 text-slate-400 border-slate-500/20',
}

export function SourceBadge({ source }: { source: string }) {
  const cls = COLORS[source] ?? COLORS.mock
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium uppercase tracking-wide ${cls}`}>
      {source}
    </span>
  )
}
