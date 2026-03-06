import { useStore } from '../../store'

export function WebSocketStatus() {
  const connected = useStore((s) => s.wsConnected)
  return (
    <div className="flex items-center gap-1.5 text-xs">
      <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-500'}`} />
      <span className={connected ? 'text-emerald-400' : 'text-red-400'}>
        {connected ? 'LIVE' : 'OFFLINE'}
      </span>
    </div>
  )
}
