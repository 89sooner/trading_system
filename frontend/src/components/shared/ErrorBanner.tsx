import { cn } from '@/lib/utils'
import { userMessageForError } from '@/api/client'

interface ErrorBannerProps {
  error: unknown
  className?: string
}

export function ErrorBanner({ error, className }: ErrorBannerProps) {
  const message = userMessageForError(error)
  return (
    <div className={cn('rounded-md border border-red-800 bg-red-950 px-4 py-3 text-sm text-red-300', className)}>
      {message}
    </div>
  )
}
