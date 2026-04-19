'use client'

import { useState, useTransition } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter, DialogClose,
} from '@/components/ui/dialog'
import { postDashboardControl } from '@/lib/api/dashboard'
import { queryClient } from '@/lib/queryClient'
import { userMessageForError } from '@/lib/api/client'
import { Pause, Play, RotateCcw, Square } from 'lucide-react'

export function ControlButtons() {
  const [isPending, startTransition] = useTransition()
  const [resetOpen, setResetOpen] = useState(false)
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null)

  async function sendControl(action: 'pause' | 'resume' | 'reset' | 'stop') {
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
    <>
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button variant="outline" size="sm" onClick={() => sendControl('pause')} disabled={isPending}>
          <Pause className="mr-1 h-3 w-3" /> Pause
        </Button>
        <Button variant="outline" size="sm" onClick={() => sendControl('resume')} disabled={isPending}>
          <Play className="mr-1 h-3 w-3" /> Resume
        </Button>
        <Button variant="outline" size="sm" onClick={() => sendControl('stop')} disabled={isPending}>
          <Square className="mr-1 h-3 w-3" /> Stop
        </Button>
        <Button variant="destructive" size="sm" onClick={() => setResetOpen(true)} disabled={isPending}>
          <RotateCcw className="mr-1 h-3 w-3" /> Reset
        </Button>
      </div>
      {message && (
        <p className={`max-w-sm text-right text-xs ${message.isError ? 'text-danger' : 'text-success'}`}>
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
            <DialogClose>
              <Button variant="outline" size="sm">Cancel</Button>
            </DialogClose>
            <Button
              variant="destructive"
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
    </>
  )
}
