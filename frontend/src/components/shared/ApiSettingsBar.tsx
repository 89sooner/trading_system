import { useState } from 'react'
import { useApiStore } from '@/store/apiStore'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Settings } from 'lucide-react'

export function ApiSettingsBar() {
  const { baseUrl, apiKey, setBaseUrl, setApiKey } = useApiStore()
  const [open, setOpen] = useState(false)
  const [urlDraft, setUrlDraft] = useState(baseUrl)
  const [keyDraft, setKeyDraft] = useState(apiKey)

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        <Settings className="h-3 w-3" />
        API
      </button>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <Input
        value={urlDraft}
        onChange={(e) => setUrlDraft(e.target.value)}
        placeholder="API base URL"
        className="h-7 w-64 text-xs"
      />
      <Input
        value={keyDraft}
        onChange={(e) => setKeyDraft(e.target.value)}
        placeholder="API Key (optional)"
        type="password"
        className="h-7 w-40 text-xs"
      />
      <Button
        size="sm"
        className="h-7 text-xs"
        onClick={() => {
          setBaseUrl(urlDraft)
          setApiKey(keyDraft)
          setOpen(false)
        }}
      >
        Save
      </Button>
      <button onClick={() => setOpen(false)} className="text-xs text-zinc-500 hover:text-zinc-300">
        X
      </button>
    </div>
  )
}
