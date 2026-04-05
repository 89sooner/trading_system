'use client'

export default function PatternSetDetailError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-20">
      <p className="text-sm text-danger">Failed to load pattern set.</p>
      <p className="text-xs text-muted-foreground">{error.message}</p>
      <button onClick={reset} className="rounded bg-secondary px-3 py-1.5 text-sm text-secondary-foreground hover:bg-secondary/80">Try again</button>
    </div>
  )
}
