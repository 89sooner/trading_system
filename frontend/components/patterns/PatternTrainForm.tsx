'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useQueryClient } from '@tanstack/react-query'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { trainPatterns, savePatternSet } from '@/lib/api/patterns'
import { parseExamples } from '@/lib/patternParser'
import { userMessageForError } from '@/lib/api/client'
import { PatternPreviewTable } from '@/components/patterns/PatternPreviewTable'
import type { PatternSetDTO } from '@/lib/api/types'

export function PatternTrainForm() {
  const qc = useQueryClient()
  const [latestPreview, setLatestPreview] = useState<PatternSetDTO | null>(null)
  const [savedId, setSavedId] = useState<string | null>(null)
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null)
  const [isTraining, setIsTraining] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  async function handleTrain(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    setIsTraining(true)
    setLatestPreview(null)
    setSavedId(null)
    setMessage({ text: 'Training preview...', isError: false })
    try {
      const payload = {
        name: String(fd.get('patternName')).trim(),
        symbol: String(fd.get('patternSymbol')).trim().toUpperCase(),
        default_threshold: Number(fd.get('patternThreshold')),
        examples: parseExamples(String(fd.get('patternExamples'))),
      }
      const preview = await trainPatterns(payload)
      setLatestPreview(preview)
      setMessage({ text: `Preview ready: ${preview.pattern_set_id}`, isError: false })
    } catch (err) {
      setMessage({ text: userMessageForError(err), isError: true })
    } finally {
      setIsTraining(false)
    }
  }

  async function handleSave() {
    if (!latestPreview) return
    setIsSaving(true)
    setMessage({ text: 'Saving...', isError: false })
    try {
      const saved = await savePatternSet(latestPreview)
      setSavedId(saved.pattern_set_id)
      await qc.invalidateQueries({ queryKey: ['patterns'] })
      setMessage({ text: `Saved: ${saved.pattern_set_id}`, isError: false })
    } catch (err) {
      setMessage({ text: userMessageForError(err), isError: true })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={handleTrain} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <Label htmlFor="patternName">Name</Label>
          <Input id="patternName" name="patternName" required placeholder="Morning Breakout" />
        </div>
        <div className="space-y-1">
          <Label htmlFor="patternSymbol">Symbol</Label>
          <Input id="patternSymbol" name="patternSymbol" required placeholder="BTCUSDT" />
        </div>
        <div className="space-y-1">
          <Label htmlFor="patternThreshold">Default Threshold</Label>
          <Input id="patternThreshold" name="patternThreshold" type="number" step="0.01" min="0" max="1" defaultValue="0.65" />
        </div>
        <div className="col-span-full space-y-1">
          <Label htmlFor="patternExamples">Examples</Label>
          <Textarea
            id="patternExamples"
            name="patternExamples"
            rows={8}
            placeholder={'label=bullish\n2024-01-01T00:00:00Z,100,110,95,105,1000\n\nlabel=bearish\n2024-01-02T00:00:00Z,105,106,90,92,1200'}
          />
        </div>
        <div className="col-span-full flex items-center gap-2">
          <Button type="submit" disabled={isTraining}>
            {isTraining ? 'Training...' : 'Train Preview'}
          </Button>
          <Button type="button" variant="outline" disabled={!latestPreview || isSaving} onClick={handleSave}>
            {isSaving ? 'Saving...' : 'Save Pattern Set'}
          </Button>
          {savedId && (
            <Link href={`/patterns/${savedId}`} className="ml-2 text-xs text-info hover:underline">
              Open Detail →
            </Link>
          )}
        </div>
      </form>

      {message && (
        <p className={`text-xs ${message.isError ? 'text-danger' : 'text-success'}`}>
          {message.text}
        </p>
      )}

      {latestPreview && <PatternPreviewTable patterns={latestPreview.patterns} />}
    </div>
  )
}
