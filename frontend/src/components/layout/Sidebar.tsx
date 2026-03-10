import { NavLink } from 'react-router-dom'
import { useStore } from '../../store'
import { WebSocketStatus } from '../ui/WebSocketStatus'

const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/watchlist', label: 'Watchlist' },
  { to: '/market', label: 'Market' },
  { to: '/settings', label: 'Settings' },
]

export function Sidebar() {
  const { unreadCount, resetUnread, setToken } = useStore()

  return (
    <aside className="w-56 flex-shrink-0 bg-slate-50 border-r border-border flex flex-col">
      {/* Logo */}
      <div className="px-6 py-8 border-b border-border/60">
        <div className="flex flex-col gap-1">
          <div className="font-bold tracking-tight text-base text-content-primary leading-none">SentinelIQ</div>
          <div className="text-[10px] font-semibold text-slate-400 tracking-[0.1em] uppercase">Market Intelligence</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-4 py-6 space-y-0.5">
        {NAV.map(({ to, label }) => (
          <NavLink key={to} to={to} end={to === '/'}
            className={({ isActive }) =>
              `flex items-center px-3 py-2 rounded-md text-[13px] transition-all relative
               ${isActive ? 'bg-slate-900/5 text-slate-900 font-semibold' : 'text-slate-500 font-medium hover:text-slate-900 hover:bg-slate-400/5'}`
            }>
            {label}
            {label === 'Alerts' && unreadCount > 0 && (
              <span className="ml-auto bg-slate-900 text-white text-[10px] font-bold px-1.5 py-0.5 rounded-sm min-w-[1.2rem] text-center tracking-wide">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-4 py-6 border-t border-border/40 space-y-5">
        <WebSocketStatus />
        <button onClick={() => { setToken(null); resetUnread() }}
          className="text-[11px] font-semibold text-slate-400 hover:text-red-600 transition-colors w-full px-3 text-left uppercase tracking-wider">
          Logout
        </button>
      </div>
    </aside>
  )
}
