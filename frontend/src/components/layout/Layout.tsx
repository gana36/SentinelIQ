import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { useWebSocket } from '../../hooks/useWebSocket'

export function Layout() {
  useWebSocket() // start WS connection for the whole session
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
