'use client'

import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { PatternTrainForm } from '@/components/patterns/PatternTrainForm'
import { PatternSetsTable } from '@/components/patterns/PatternSetsTable'
import { listPatternSets } from '@/lib/api/patterns'
import { RefreshCw } from 'lucide-react'

export default function PatternsPage() {
  const { data, refetch } = useQuery({
    queryKey: ['patterns'],
    queryFn: listPatternSets,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pattern Management"
        description="Train and manage candlestick pattern sets"
      />

      <Card>
        <CardHeader><CardTitle>Train Pattern Set</CardTitle></CardHeader>
        <CardContent><PatternTrainForm /></CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Saved Pattern Sets</CardTitle>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="mr-1 h-3 w-3" /> Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <PatternSetsTable patternSets={data ?? []} />
        </CardContent>
      </Card>
    </div>
  )
}
