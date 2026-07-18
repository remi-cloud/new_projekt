import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Start', end: true },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/okazje', label: 'Okazje' },
  { to: '/cykle', label: 'Cykle' },
  { to: '/historia', label: 'Historia' },
  { to: '/rynki', label: 'Rynki' },
]

export default function Layout() {
  return (
    <div className="shell">
      <div className="shell-glow" aria-hidden />
      <header className="topbar">
        <NavLink to="/" className="brand">
          <span className="brand-mark">CT</span>
          <span className="brand-text">Cyclical Trader</span>
        </NavLink>
        <nav className="nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        Cyclical Trader · Krypto: cykl 364d + 1064d od ATH · Tradycyjne: cykl prezydencki USA ·
        Nie jest to porada inwestycyjna
      </footer>
    </div>
  )
}
