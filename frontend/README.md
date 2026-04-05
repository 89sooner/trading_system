# Trading System — Frontend

Next.js 16 + App Router frontend for the trading system operator UI.

## Stack

- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS v4 + CSS variables (semantic tokens)
- **UI Primitives**: Base UI (`@base-ui/react`) + shadcn-compatible component wrappers
- **Charts**: Recharts
- **State**: Zustand (operator API settings)
- **Data fetching**: TanStack Query v5
- **Forms**: react-hook-form + zod

## Getting Started

```bash
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | Backend API base URL |

The base URL and API key can also be changed at runtime via the **ApiSettingsBar** in the top nav (persisted in localStorage).

## Routes

| Path | Description |
|---|---|
| `/` | Redirect to dashboard |
| `/dashboard` | Live trading system monitoring (5 s polling) |
| `/runs` | Backtest run history |
| `/runs/[runId]` | Run detail — equity curve, drawdown, trade analytics, signals, fills |
| `/strategies` | Strategy profiles — list and create |
| `/patterns` | Pattern sets — list and train |
| `/patterns/[patternSetId]` | Pattern set detail |
| `/admin` | Admin operations |

## Scripts

```bash
npm run dev      # development server
npm run build    # production build
npm run lint     # ESLint
```

## Design System

Semantic color tokens defined in `app/globals.css`:

- `success`, `danger`, `warning`, `info`, `muted`

Domain components in `components/domain/`:

- `MetricCard` — numeric KPI tile with trend indicator
- `DataTable` — column-defined table with empty/loading states
- `StatusIndicator` — dot + label (online/offline/warning/error)
- `ChartContainer` — chart wrapper with loading/empty/error states
- `StatTile`, `StatusBadge`, `ErrorBanner`

## Backend

See the root `README.md` for backend setup and the full run script.
