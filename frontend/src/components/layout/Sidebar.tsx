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
    <aside className="w-56 flex-shrink-0 bg-slate-50 border-r border-border flex flex-col">
      {/* Logo */}
      <div className="px-5 py-6 border-b border-border/60">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-emerald-50 rounded-lg flex items-center justify-center border border-emerald-100">
            <Zap className="w-4 h-4 text-emerald-500" />
          </div>
          <div>
            <div className="font-semibold tracking-tight text-sm text-content-primary leading-none">SentinelIQ</div>
            <div className="text-[10.5px] font-medium text-slate-400 mt-0.5 tracking-wide uppercase">Market Intelligence</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors relative
               ${isActive ? 'bg-slate-900/5 text-slate-900 font-semibold' : 'text-slate-500 font-medium hover:text-slate-900 hover:bg-slate-400/5'}`
            }>
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
            {label === 'Alerts' && unreadCount > 0 && (
              <span className="ml-auto bg-slate-900 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-md min-w-[1.2rem] text-center tracking-wide shadow-sm">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-4 py-4 space-y-3">
        <WebSocketStatus />
        <button onClick={() => { setToken(null); resetUnread() }}
          className="flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-slate-900 transition-colors w-full px-1">
          <LogOut className="w-3.5 h-3.5" />Logout
        </button>
      </div>
    </aside>
  )
}
