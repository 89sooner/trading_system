import { Link } from '@tanstack/react-router'

const NAV_LINKS = [
  { to: '/', label: 'New Run' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/runs', label: 'Runs' },
  { to: '/patterns', label: 'Patterns' },
  { to: '/strategies', label: 'Strategies' },
] as const

export function NavBar() {
  return (
    <nav className="flex items-center gap-1">
      {NAV_LINKS.map((link) => (
        <Link
          key={link.to}
          to={link.to}
          className="rounded px-3 py-1.5 text-sm text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition-colors"
          activeProps={{ className: 'rounded px-3 py-1.5 text-sm bg-zinc-800 text-zinc-100 font-medium' }}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  )
}
