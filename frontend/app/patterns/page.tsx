'use client'

import { RefreshCw, Shapes, Sparkles } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { PatternSetsTable } from '@/components/patterns/PatternSetsTable'
import { PatternTrainForm } from '@/components/patterns/PatternTrainForm'
import { PageHeader } from '@/components/layout/PageHeader'
import { SurfacePanel } from '@/components/layout/SurfacePanel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { listPatternSets } from '@/lib/api/patterns'

export default function PatternsPage() {
  const { data, refetch } = useQuery({
    queryKey: ['patterns'],
    queryFn: listPatternSets,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pattern Management"
        description="Train reusable pattern sets, review the preview output, and keep a clean library of signal ingredients."
        actions={
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">Preview before save</Badge>
            <Badge variant="outline">Repository-backed</Badge>
            <Badge variant="outline">Pattern-signal ready</Badge>
          </div>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.8fr)]">
        <SurfacePanel
          eyebrow="Training"
          title="Train a pattern set"
          description="Build a preview from curated examples, inspect the output, then save the set into the shared pattern library."
          action={<Sparkles className="h-4 w-4 text-muted-foreground" />}
        >
          <PatternTrainForm />
        </SurfacePanel>

        <SurfacePanel
          eyebrow="Guide"
          title="Working rhythm"
          description="Keep training inputs and saved assets clean enough for strategy promotion."
          action={<Shapes className="h-4 w-4 text-muted-foreground" />}
        >
          <div className="space-y-3 text-sm text-muted-foreground">
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              Use short, clearly labeled examples. Mixed-quality examples make the preview harder to interpret later.
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              Save only the previews you are willing to reference from a strategy profile. The pattern library should stay reviewable.
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              Open a saved pattern set to inspect labels, thresholds, and prototypes before wiring it into a run.
            </div>
          </div>
        </SurfacePanel>
      </div>

      <SurfacePanel
        eyebrow="Library"
        title="Saved pattern sets"
        description="Repository-backed pattern sets that can be reused by strategy profiles and backtest runs."
        action={
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-1 h-3 w-3" /> Refresh
          </Button>
        }
      >
        <PatternSetsTable patternSets={data ?? []} />
      </SurfacePanel>
    </div>
  )
}
