import type { Metadata } from 'next'
import { Providers } from '@/components/providers'
import { NavBar } from '@/components/layout/NavBar'
import { ApiSettingsBar } from '@/components/shared/ApiSettingsBar'
import './globals.css'

export const metadata: Metadata = {
  title: 'Trading System',
  description: 'Trading System Dashboard',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      className="dark"
    >
      <body className="min-h-screen bg-background text-foreground antialiased">
        <Providers>
          <header className="border-b border-border bg-card px-4 py-3">
            <div className="mx-auto flex max-w-7xl items-center justify-between">
              <div className="flex items-center gap-4">
                <span className="text-sm font-semibold">Trading System</span>
                <NavBar />
              </div>
              <ApiSettingsBar />
            </div>
          </header>
          <main className="mx-auto max-w-7xl px-4 py-6">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  )
}
