'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

const NAV_LINKS = [
  { href: '/', label: 'New Run' },
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/dashboard/sessions', label: 'Sessions' },
  { href: '/runs', label: 'Runs' },
  { href: '/patterns', label: 'Patterns' },
  { href: '/strategies', label: 'Strategies' },
  { href: '/admin', label: 'Admin' },
] as const

export function NavBar() {
  const pathname = usePathname()

  return (
    <nav className="flex items-center gap-1">
      {NAV_LINKS.map((link) => {
        const isActive = link.href === '/' || link.href === '/dashboard'
          ? pathname === link.href
          : pathname.startsWith(link.href)
        return (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              'rounded px-3 py-1.5 text-sm transition-colors',
              isActive
                ? 'bg-secondary text-secondary-foreground font-medium'
                : 'text-muted-foreground hover:bg-secondary hover:text-secondary-foreground',
            )}
          >
            {link.label}
          </Link>
        )
      })}
    </nav>
  )
}
