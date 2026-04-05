'use client'

import { useQuery } from '@tanstack/react-query'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StrategyForm } from '@/components/strategies/StrategyForm'
import { StrategiesTable } from '@/components/strategies/StrategiesTable'
import { listStrategyProfiles } from '@/lib/api/strategies'
import { RefreshCw } from 'lucide-react'

export default function StrategiesPage() {
  const { data, refetch } = useQuery({
    queryKey: ['strategies'],
    queryFn: listStrategyProfiles,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="Strategy Profiles"
        description="Manage trading strategy profiles"
      />

      <Card>
        <CardHeader><CardTitle>Create Strategy Profile</CardTitle></CardHeader>
        <CardContent><StrategyForm /></CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Saved Strategies</CardTitle>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="mr-1 h-3 w-3" /> Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <StrategiesTable strategies={data ?? []} />
        </CardContent>
      </Card>
    </div>
  )
}
