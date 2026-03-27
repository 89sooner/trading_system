import { createRootRoute, Outlet } from '@tanstack/react-router'
import { NavBar } from '@/components/layout/NavBar'
import { ApiSettingsBar } from '@/components/shared/ApiSettingsBar'

export const Route = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-zinc-950">
      <header className="border-b border-zinc-800 bg-zinc-900 px-4 py-3">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm font-semibold text-zinc-100">Trading System</span>
            <NavBar />
          </div>
          <ApiSettingsBar />
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  ),
})
