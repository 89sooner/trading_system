'use client'

import { RefreshCw, SlidersHorizontal, Target } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '@/components/layout/PageHeader'
import { SurfacePanel } from '@/components/layout/SurfacePanel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { StrategyForm } from '@/components/strategies/StrategyForm'
import { StrategiesTable } from '@/components/strategies/StrategiesTable'
import { listStrategyProfiles } from '@/lib/api/strategies'

export default function StrategiesPage() {
  const { data, refetch } = useQuery({
    queryKey: ['strategies'],
    queryFn: listStrategyProfiles,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Strategy Profiles"
        description="Turn saved pattern sets into reusable execution rules with explicit mappings, thresholds, and trade sizing."
        actions={
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">Pattern-linked</Badge>
            <Badge variant="outline">Reusable inputs</Badge>
            <Badge variant="outline">Promotion-ready</Badge>
          </div>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.8fr)]">
        <SurfacePanel
          eyebrow="Authoring"
          title="Create a strategy profile"
          description="Bind pattern labels to execution sides and keep the configuration reusable across backtests and live preflight."
          action={<Target className="h-4 w-4 text-muted-foreground" />}
        >
          <StrategyForm />
        </SurfacePanel>

        <SurfacePanel
          eyebrow="Guide"
          title="Strategy design notes"
          description="Keep saved profiles explicit enough for operators to review quickly."
          action={<SlidersHorizontal className="h-4 w-4 text-muted-foreground" />}
        >
          <div className="space-y-3 text-sm text-muted-foreground">
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              Prefer meaningful strategy IDs that survive copy, comparison, and promotion into run history.
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              Use threshold overrides only when the saved pattern set really needs per-label treatment.
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              Keep label-to-side mappings obvious. Hidden complexity here becomes operator risk later.
            </div>
          </div>
        </SurfacePanel>
      </div>

      <SurfacePanel
        eyebrow="Library"
        title="Saved strategies"
        description="The strategy profiles currently available for run creation and pattern-signal execution."
        action={
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-1 h-3 w-3" /> Refresh
          </Button>
        }
      >
        <StrategiesTable strategies={data ?? []} />
      </SurfacePanel>
    </div>
  )
}
