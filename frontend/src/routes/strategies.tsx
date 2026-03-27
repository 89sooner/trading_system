import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StrategyForm } from '@/components/strategies/StrategyForm'
import { StrategiesTable } from '@/components/strategies/StrategiesTable'
import { listStrategyProfiles } from '@/api/strategies'

export const Route = createFileRoute('/strategies')({
  component: StrategiesPage,
})

function StrategiesPage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['strategies'],
    queryFn: listStrategyProfiles,
  })

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-zinc-100">Strategy Profiles</h1>
      <Card>
        <CardHeader><CardTitle>Create Strategy Profile</CardTitle></CardHeader>
        <CardContent><StrategyForm /></CardContent>
      </Card>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Saved Strategies</CardTitle>
            <Button variant="outline" size="sm" onClick={() => refetch()}>Refresh</Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading
            ? <p className="text-xs text-zinc-500">Loading...</p>
            : <StrategiesTable strategies={data ?? []} />
          }
        </CardContent>
      </Card>
    </div>
  )
}
