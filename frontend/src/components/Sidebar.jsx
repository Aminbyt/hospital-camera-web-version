import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/live', label: 'Live Cameras' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/events', label: 'Events / History' },
  { to: '/settings', label: 'Settings' },
]

export default function Sidebar() {
  return (
    <div className="sidebar">
      <div className="sidebar-brand">
        HOSPITAL CAMERA AI
        <span>MONITORING CONSOLE</span>
      </div>
      <nav className="sidebar-nav">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => 'sidebar-link' + (isActive ? ' active' : '')}
          >
            {l.label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-foot">
        BACKEND · localhost:8000<br />
        All cameras, thresholds and<br />bot settings are configured live<br />from this console.
      </div>
    </div>
  )
}
