import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Bell, Star, BarChart2, Settings, Zap, LogOut } from 'lucide-react'
import { useStore } from '../../store'
import { WebSocketStatus } from '../ui/WebSocketStatus'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/alerts', icon: Bell, label: 'Alerts' },
  { to: '/watchlist', icon: Star, label: 'Watchlist' },
  { to: '/market', icon: BarChart2, label: 'Market' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
  const { unreadCount, resetUnread, setToken } = useStore()

  return (
    <aside className="w-56 flex-shrink-0 bg-page border-r border-border flex flex-col">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-emerald-500 rounded-lg flex items-center justify-center">
            <Zap className="w-4 h-4 text-black" />
          </div>
          <div>
            <div className="font-semibold tracking-tight text-sm text-content-primary leading-none">SentinelIQ</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Market Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors relative
               ${isActive ? 'bg-surface-selected text-content-primary' : 'text-content-secondary hover:text-content-primary hover:bg-surface-hover'}`
            }>
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
            {label === 'Alerts' && unreadCount > 0 && (
              <span className="ml-auto bg-emerald-500 text-black text-xs font-medium px-1.5 py-0.5 rounded-full min-w-[1.2rem] text-center">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-3 py-3 border-t border-border space-y-2">
        <WebSocketStatus />
        <button onClick={() => { setToken(null); resetUnread() }}
          className="flex items-center gap-2 text-xs text-slate-500 hover:text-red-400 transition-colors w-full px-1">
          <LogOut className="w-3.5 h-3.5" />Logout
        </button>
      </div>
    </aside>
  )
}
