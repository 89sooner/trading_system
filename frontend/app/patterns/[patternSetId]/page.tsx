'use client'

import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatTile } from '@/components/domain/StatTile'
import { ErrorBanner } from '@/components/domain/ErrorBanner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PatternPreviewTable } from '@/components/patterns/PatternPreviewTable'
import { getPatternSet } from '@/lib/api/patterns'

export default function PatternSetDetailPage({
  params,
}: {
  params: Promise<{ patternSetId: string }>
}) {
  const { patternSetId } = use(params)

  const { data, isLoading, error } = useQuery({
    queryKey: ['pattern', patternSetId],
    queryFn: () => getPatternSet(patternSetId),
    staleTime: Infinity,
  })

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading...</p>
  if (error) return <ErrorBanner error={error} />
  if (!data) return null

  return (
    <div className="space-y-6">
      <PageHeader title={data.name} description={data.pattern_set_id} />

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <StatTile label="Symbol" value={data.symbol} />
        <StatTile label="Threshold" value={String(data.default_threshold)} />
        <StatTile label="Examples" value={String(data.examples_count)} />
        <StatTile label="Patterns" value={String(data.patterns.length)} />
      </div>

      <Card>
        <CardHeader><CardTitle>Patterns</CardTitle></CardHeader>
        <CardContent><PatternPreviewTable patterns={data.patterns} /></CardContent>
      </Card>
    </div>
  )
}
