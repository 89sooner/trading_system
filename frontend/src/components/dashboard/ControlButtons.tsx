import { useState, useTransition } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter, DialogClose,
} from '@/components/ui/dialog'
import { postDashboardControl } from '@/api/dashboard'
import { queryClient } from '@/lib/queryClient'
import { userMessageForError } from '@/api/client'

export function ControlButtons() {
  const [isPending, startTransition] = useTransition()
  const [resetOpen, setResetOpen] = useState(false)
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null)

  async function sendControl(action: 'pause' | 'resume' | 'reset') {
    startTransition(async () => {
      try {
        const data = await postDashboardControl(action)
        setMessage({ text: `'${action}' applied. State: ${data.state}`, isError: false })
        await queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      } catch (e) {
        setMessage({ text: userMessageForError(e), isError: true })
      }
    })
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Button variant="warn" size="sm" onClick={() => sendControl('pause')} disabled={isPending}>
          Pause
        </Button>
        <Button variant="bull" size="sm" onClick={() => sendControl('resume')} disabled={isPending}>
          Resume
        </Button>
        <Button variant="bear" size="sm" onClick={() => setResetOpen(true)} disabled={isPending}>
          Reset
        </Button>
      </div>
      {message && (
        <p className={`text-xs ${message.isError ? 'text-red-400' : 'text-green-400'}`}>
          {message.text}
        </p>
      )}

      <Dialog open={resetOpen} onOpenChange={setResetOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Reset</DialogTitle>
            <DialogDescription>
              This will clear EMERGENCY state and return the runtime to PAUSED. Continue?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" size="sm">Cancel</Button>
            </DialogClose>
            <Button
              variant="bear"
              size="sm"
              onClick={() => {
                setResetOpen(false)
                sendControl('reset')
              }}
            >
              Reset
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
