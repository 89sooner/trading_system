import { userMessageForError } from '@/lib/api/client'

export function ErrorBanner({ error }: { error: unknown }) {
  return (
    <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3">
      <p className="text-sm text-danger">{userMessageForError(error)}</p>
    </div>
  )
}
