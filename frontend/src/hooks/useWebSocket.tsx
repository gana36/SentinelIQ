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
      const backendUrl = import.meta.env.VITE_API_URL ?? `${window.location.protocol}//${window.location.host}`
      const wsProtocol = backendUrl.startsWith('https') ? 'wss' : 'ws'
      const wsHost = backendUrl.replace(/^https?:\/\//, '')
      const ws = new WebSocket(`${wsProtocol}://${wsHost}/api/v1/ws/alerts?token=${token}`)
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
            ), { id: card.alert_id, duration: 6000 })
          }
        } catch { }
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
    <div className="bg-card border border-border rounded-xl p-3 min-w-[280px] shadow-lg animate-slide-in">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-mono font-semibold tracking-tight text-content-primary">${card.ticker}</span>
        <span className={`text-xs font-medium ${sentimentColor}`}>
          {card.sentiment?.label?.toUpperCase()}
        </span>
        <span className="ml-auto text-xs text-slate-500">LIVE</span>
      </div>
      <p className="text-xs text-content-secondary line-clamp-2">{card.event_summary}</p>
    </div>
  )
}
