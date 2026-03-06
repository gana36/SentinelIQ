import { useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { useStore } from '../store'
import type { ActionCard } from '../types'

export function useWebSocket() {
  const token = useStore((s) => s.token)
  const { addLiveAlert, setWsConnected, incrementUnread } = useStore()
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (!token) return

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${protocol}://${window.location.host}/api/v1/ws/alerts?token=${token}`)
      wsRef.current = ws

      ws.onopen = () => {
        setWsConnected(true)
        console.log('[WS] connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'heartbeat' || data.type === 'pong') return
          const payload = data.raw ? JSON.parse(data.raw) : data
          if (payload.ticker) {
            const card = payload as ActionCard
            addLiveAlert(card)
            incrementUnread()
            toast.custom(() => (
              <AlertToastContent card={card} />
            ), { duration: 6000 })
          }
        } catch {}
      }

      ws.onclose = () => {
        setWsConnected(false)
        reconnectTimer.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => ws.close()

      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
      }, 25_000)

      return () => clearInterval(ping)
    }

    const cleanup = connect()
    return () => {
      cleanup?.()
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [token])
}

function AlertToastContent({ card }: { card: ActionCard }) {
  const sentimentColor = card.sentiment?.label === 'positive'
    ? 'text-emerald-400' : card.sentiment?.label === 'negative' ? 'text-red-400' : 'text-slate-400'
  return (
    <div className="bg-[#111318] border border-[#1e2130] rounded-xl p-3 min-w-[280px] animate-slide-in">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-mono font-bold text-white">${card.ticker}</span>
        <span className={`text-xs font-medium ${sentimentColor}`}>
          {card.sentiment?.label?.toUpperCase()}
        </span>
        <span className="ml-auto text-xs text-slate-500">LIVE</span>
      </div>
      <p className="text-xs text-slate-400 line-clamp-2">{card.event_summary}</p>
    </div>
  )
}
