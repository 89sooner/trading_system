'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { trainPatterns, savePatternSet } from '@/lib/api/patterns'
import { parseExamples } from '@/lib/patternParser'
import { userMessageForError } from '@/lib/api/client'
import { PatternPreviewTable } from '@/components/patterns/PatternPreviewTable'
import type { PatternSetDTO } from '@/lib/api/types'

const schema = z.object({
  name: z.string().min(1, 'Required'),
  symbol: z.string().min(1, 'Required'),
  threshold: z.string().refine(
    (v) => !isNaN(Number(v)) && Number(v) >= 0 && Number(v) <= 1,
    { message: 'Must be a number between 0 and 1' },
  ),
  examples: z.string().min(1, 'Provide at least one example block'),
})

type FormValues = z.infer<typeof schema>

export function PatternTrainForm() {
  const qc = useQueryClient()
  const [latestPreview, setLatestPreview] = useState<PatternSetDTO | null>(null)
  const [savedId, setSavedId] = useState<string | null>(null)
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { threshold: '0.65' },
  })

  async function onTrain(values: FormValues) {
    setLatestPreview(null)
    setSavedId(null)
    setMessage({ text: 'Training preview...', isError: false })
    try {
      const preview = await trainPatterns({
        name: values.name,
        symbol: values.symbol.toUpperCase(),
        default_threshold: Number(values.threshold),
        examples: parseExamples(values.examples),
      })
      setLatestPreview(preview)
      setMessage({ text: `Preview ready: ${preview.pattern_set_id}`, isError: false })
    } catch (err) {
      setMessage({ text: userMessageForError(err), isError: true })
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
      <form onSubmit={handleSubmit(onTrain)} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <Label htmlFor="name">Name</Label>
          <Input id="name" placeholder="Morning Breakout" {...register('name')} />
          {errors.name && <p className="text-xs text-danger">{errors.name.message}</p>}
        </div>

        <div className="space-y-1">
          <Label htmlFor="symbol">Symbol</Label>
          <Input id="symbol" placeholder="BTCUSDT" {...register('symbol')} />
          {errors.symbol && <p className="text-xs text-danger">{errors.symbol.message}</p>}
        </div>

        <div className="space-y-1">
          <Label htmlFor="threshold">Default Threshold</Label>
          <Input id="threshold" type="number" step="0.01" min="0" max="1" {...register('threshold')} />
          {errors.threshold && <p className="text-xs text-danger">{errors.threshold.message}</p>}
        </div>

        <div className="col-span-full space-y-1">
          <Label htmlFor="examples">Examples</Label>
          <Textarea
            id="examples"
            rows={8}
            placeholder={'label=bullish\n2024-01-01T00:00:00Z,100,110,95,105,1000\n\nlabel=bearish\n2024-01-02T00:00:00Z,105,106,90,92,1200'}
            {...register('examples')}
          />
          {errors.examples && <p className="text-xs text-danger">{errors.examples.message}</p>}
        </div>

        <div className="col-span-full flex items-center gap-2">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Training...' : 'Train Preview'}
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
