# Production Deployment — Supabase · Railway · Vercel

## Purpose

Step-by-step procedure for deploying the trading system to production
using the Phase 9 infrastructure stack.

- **Supabase** — PostgreSQL database (run persistence, equity timeseries)
- **Railway** — FastAPI backend (all API endpoints including SSE streaming)
- **Vercel** — Next.js frontend

Follow the steps in order.
Each step has an explicit Exit criteria — do not skip verification.

---

## Prerequisites

### Accounts required

| Service | Purpose | URL |
|---------|---------|-----|
| Supabase | PostgreSQL DB | https://supabase.com |
| Railway | FastAPI backend hosting | https://railway.app |
| Vercel | Next.js frontend hosting | https://vercel.com |
| GitHub | Source repository | https://github.com |

### Local tools

```bash
psql --version        # PostgreSQL client (for running migrations)
git --version
node --version        # 18 or higher
```

If `psql` is unavailable, use the Supabase dashboard SQL Editor instead.

### Codebase health check

```bash
# Confirm main branch is clean
git status
git log --oneline -5

# Confirm local tests pass
pytest --tb=short -q
ruff check src/ tests/
```

Only proceed when local tests pass.

---

## Step 1. Supabase — Database Setup

### 1-1. Create project

1. Log in at https://supabase.com.
2. Click **New project**.
3. Fill in:
   - **Name**: `trading-system` (or any name)
   - **Database Password**: generate a strong password and **save it immediately**.
     This password is part of `DATABASE_URL`.
   - **Region**: choose the region closest to your users (e.g. Northeast Asia).
4. Click **Create new project** and wait for provisioning (about 1–2 minutes).

### 1-2. Copy the connection string

1. Left sidebar → **Project Settings** → **Database** tab.
2. Under **Connection string**, select the **URI** tab.
3. Copy the string: `postgresql://postgres:[YOUR-PASSWORD]@db.[ref].supabase.co:5432/postgres`
4. Replace `[YOUR-PASSWORD]` with the password from step 1-1.
5. This is your `DATABASE_URL`. Keep it in a temporary secure location.

> **Security**: Never commit `DATABASE_URL`. Store it only in `.env` (which is gitignored).

### 1-3. Run schema migrations

```bash
export DATABASE_URL="postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres"

psql "$DATABASE_URL" -f scripts/migrations/001_create_backtest_runs.sql
psql "$DATABASE_URL" -f scripts/migrations/002_create_equity_snapshots.sql
```

If `psql` is unavailable, use the **Supabase dashboard SQL Editor**:
1. Left sidebar → **SQL Editor** → **New query**.
2. Paste the contents of `scripts/migrations/001_create_backtest_runs.sql` and click **Run**.
3. Repeat for `002_create_equity_snapshots.sql`.

### 1-4. Verify table creation

In the Supabase dashboard → **Table Editor**, confirm these tables exist:
- `backtest_runs`
- `equity_snapshots`

Or verify via SQL Editor:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';
```

**Exit criteria**: Both `backtest_runs` and `equity_snapshots` tables exist.
`idx_equity_snapshots_session_ts` index is present on `equity_snapshots`.

---

## Step 2. Railway — FastAPI Backend Deployment

### 2-1. Create project and connect repository

1. Log in at https://railway.app.
2. **New Project** → **Deploy from GitHub repo**.
3. Connect your GitHub account and select this repository.
4. Railway builds the service from the repository `Dockerfile` and applies `railway.json`.
5. The container starts with `uvicorn trading_system.api.server:app`, so no extra Railway start command is required for the documented path.

### 2-2. Set environment variables

Railway dashboard → the created service → **Variables** tab.

#### Required

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgresql://postgres:[pw]@db.[ref].supabase.co:5432/postgres` | Supabase connection string from Step 1-2 |
| `TRADING_SYSTEM_ALLOWED_API_KEYS` | `your-secret-api-key` | API authentication key. Multiple keys: comma-separated |

> The `TRADING_SYSTEM_ALLOWED_API_KEYS` value must match the API key
> you will enter in the frontend UI later.
> Use a long random string, e.g. `TS-PROD-KEY-A1B2C3D4E5F6`.

#### Optional (recommended)

| Variable | Example value | Notes |
|----------|--------------|-------|
| `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` | *(set after Step 3, see 3-4)* | CORS allowed origins |
| `TRADING_SYSTEM_WEBHOOK_URL` | `https://hooks.example.com/trading` | Webhook notification URL (disabled if unset) |
| `TRADING_SYSTEM_WEBHOOK_EVENTS` | `order.filled,risk.rejected` | Comma-separated event allowlist for webhook delivery |
| `TRADING_SYSTEM_WEBHOOK_TIMEOUT` | `5` | Webhook request timeout in seconds |
| `TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS` | `120` | Requests per window per client (default: 60) |

> `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` requires the Vercel URL from Step 3.
> Add it in **Step 3-4**.

### 2-3. Confirm deployment and get URL

1. Railway dashboard → **Deployments** tab → watch build logs.
2. After a successful build, go to **Settings** → **Domains** to find
   the auto-generated URL: `https://your-service.railway.app`
3. Record this URL — you need it for the Vercel environment variable.

### 2-4. Health check

```bash
RAILWAY_URL="https://your-service.railway.app"
curl -s "$RAILWAY_URL/health"
# Expected: {"status": "ok"}
```

`/health` is intentionally exempt from API-key authentication so Railway and
other load balancers can probe container health without custom headers.

### 2-5. API connectivity check

```bash
API_KEY="your-secret-api-key"

curl -s -H "X-API-Key: $API_KEY" "$RAILWAY_URL/api/v1/backtests"
# Expected: {"runs": [], "total": 0, "page": 1, "page_size": 20}
# An empty list with 200 confirms the database connection is working.
```

**Exit criteria**: `/health` returns 200. `/api/v1/backtests` returns 200 (confirms DB connectivity).

---

## Step 3. Vercel — Frontend Deployment

### 3-1. Create project and connect repository

1. Log in at https://vercel.com.
2. **New Project** → import the GitHub repository.
3. On the **Configure Project** screen:
   - **Root Directory**: change to `frontend` (required).
   - **Framework Preset**: `Next.js` (auto-detected).
   - Leave Build Command and Output Directory at defaults.

### 3-2. Set environment variables

In the **Environment Variables** section on the Configure Project screen:

| Variable | Value | Notes |
|----------|-------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | `https://your-service.railway.app/api/v1` | Railway URL + `/api/v1`. No trailing slash. |

> The API key is **not** set as an environment variable.
> The frontend stores it in the Zustand API store via the runtime input UI.

### 3-3. Deploy

Click **Deploy** and watch the build logs.
After a successful deployment, record the Vercel URL: `https://your-app.vercel.app`

Note: the frontend build is pinned to `next build --webpack`. This avoids Turbopack process-spawn failures seen in restricted CI/sandbox environments and is the expected production build path for this repository.

### 3-4. Add Vercel URL to Railway CORS

Railway dashboard → service → **Variables** tab:

| Variable | Value |
|----------|-------|
| `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` | `https://your-app.vercel.app` |

> Multiple origins: comma-separated — `https://your-app.vercel.app,https://custom-domain.com`
> No trailing slash — CORS comparison is exact-match.

Railway auto-redeploys after the variable is saved. Wait for redeployment to complete.

---

## Step 4. Integration Verification

### 4-1. Frontend → backend connectivity

1. Open the Vercel URL in a browser.
2. Open the API key input (top-right settings icon) and enter the value
   set in `TRADING_SYSTEM_ALLOWED_API_KEYS`.
3. Confirm the dashboard loads without errors.
4. Open browser DevTools → **Network** tab and confirm no CORS errors
   (`blocked by CORS policy`).
5. In the launch console, run **Preflight** first and confirm the readiness panel shows no blocking reasons for the intended route.
6. If the dashboard is disconnected, use the launch form to start a `paper` session and confirm status changes from `idle`/`stopped` to `starting` and then `running`.

### 4-2. Runtime launch and stop

1. In the dashboard launch form, enter one or more symbols, choose provider/broker, and select `paper` or guarded `live`.
2. Run **Preflight** and verify `next_allowed_actions` includes the selected execution mode.
3. Click **Start Runtime**.
4. Confirm the dashboard status shows a new `session_id`, `controller_state=active`, the latest preflight summary, and live metrics begin updating.
5. Use **Stop** and confirm the dashboard returns to a disconnected/stopped state without leaving stale positions or SSE connections in the UI.

### 4-3. SSE streaming

```bash
RAILWAY_URL="https://tradingsystem-production-816d.up.railway.app"
API_KEY="${API_KEY:?set your production API key locally before running this command}"

# Connect to the SSE stream (expect a heartbeat within 15 seconds)
curl -N --max-time 20 -H "Accept: text/event-stream" \
  "$RAILWAY_URL/api/v1/dashboard/stream?api_key=$API_KEY"

# Expected output (every 15 seconds):
# event: heartbeat
# data: {}
#
# Press ^C to stop
```

> Security note: do not commit the production API key into tracked docs.
> Set it only in your current shell session, for example with `export API_KEY='...'`.
> If you use `--max-time 20`, the final `curl: (28) Operation timed out ...` message is
> considered a normal test stop, not an SSE failure.

### 4-4. Run persistence after redeployment

1. Run a backtest from the frontend.
2. Confirm the run appears in the `/runs` page.
3. Railway dashboard → **Redeploy** the service.
4. After redeployment completes, refresh `/runs`.
   - Run still listed → Supabase persistence is working.
   - Run missing → `DATABASE_URL` connection issue; check Railway logs.
5. When possible, confirm the same `run_id` directly in Supabase via SQL Editor or `psql`.
   Treat this as the stronger source of truth than the UI alone.

### 4-5. Verify data in Supabase

```bash
psql "$DATABASE_URL" \
  -c "SELECT run_id, status, started_at FROM backtest_runs ORDER BY created_at DESC LIMIT 5;"
```

**Exit criteria summary**:

| Check | Criterion |
|-------|-----------|
| `GET /health` | 200 `{"status": "ok"}` |
| `GET /api/v1/backtests` | 200, no CORS errors |
| Runtime launch/stop | Session starts from dashboard and stops cleanly |
| SSE `/dashboard/stream` | Heartbeat received within 15 s |
| Run list after redeploy | Previous runs preserved |
| Browser CORS | No errors in DevTools |

---

## Step 5. Custom Domains (Optional)

### Vercel custom domain

1. Vercel dashboard → **Settings** → **Domains** → add domain.
2. Configure CNAME or A record at your DNS provider.
3. Vercel auto-issues an SSL certificate.

### Railway custom domain

1. Railway dashboard → service → **Settings** → **Domains** → add custom domain.
2. Configure DNS CNAME record.
3. Update `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` to include the new domain.

---

## Troubleshooting

### Railway build fails

Check build logs: Railway dashboard → **Deployments** → failed deploy → **View Logs**.

Common causes:
- `psycopg[binary]` wheel download failure on a restricted network — retry
- Missing files in `COPY` instructions — check `Dockerfile` paths match the repository layout
- If deployment completes but the process crashes immediately with
   `ModuleNotFoundError: No module named 'httpx'`, `httpx` is likely still listed
   as a development-only dependency instead of a runtime dependency.
   Move it into `[project.dependencies]` and refresh the lockfile.

```bash
UV_CACHE_DIR=.uv-cache uv lock
git add pyproject.toml uv.lock
git commit -m "Move httpx to runtime dependencies"
git push
```

---

### `GET /health` returns 502

The container started but the process is not responding.

1. Check Railway logs for `uvicorn` startup errors.
2. Look for `psycopg.connect()` errors — indicates a bad `DATABASE_URL`.
3. Confirm `DATABASE_URL` is set and the Supabase password has no special characters
   that need URL-encoding (e.g. `@`, `#`). URL-encode them if present.
4. If the log shows `ModuleNotFoundError: No module named 'httpx'`, the webhook module
   is importing `httpx` but the production dependency set does not include it.
   Update `pyproject.toml` runtime dependencies and regenerate `uv.lock`, then redeploy.

---

### CORS error in browser (`blocked by CORS policy`)

1. Confirm `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` value is the exact Vercel URL
   with no trailing slash.
   - Correct: `https://your-app.vercel.app`
   - Wrong: `https://your-app.vercel.app/`
2. Confirm the Railway redeployment after adding the variable has completed.
3. Confirm `NEXT_PUBLIC_API_BASE_URL` includes `/api/v1`
   and does not have a trailing slash.

---

### Run list is empty after redeployment

The server is falling back to file-based storage (`data/runs/`) because
`DATABASE_URL` is not being read correctly.

1. Confirm `DATABASE_URL` is set in Railway Variables (not just locally).
2. Check Railway logs at startup for connection errors.
3. Update the variable and **Redeploy**.

---

### SSE connection drops immediately

1. Confirm the `api_key` query parameter is correct.
2. Check Railway logs for authentication or stream setup errors.
3. Confirm `/health` is responding — if 502, fix the backend first.

---

## Environment Variable Reference

### Railway

```
# Required
DATABASE_URL=postgresql://postgres:[pw]@db.[ref].supabase.co:5432/postgres
TRADING_SYSTEM_ALLOWED_API_KEYS=your-secret-api-key

# CORS — Vercel deployment URL (add after Step 3)
TRADING_SYSTEM_CORS_ALLOW_ORIGINS=https://your-app.vercel.app

# Optional
TRADING_SYSTEM_WEBHOOK_URL=
TRADING_SYSTEM_WEBHOOK_EVENTS=order.filled,risk.rejected,pattern.alert,system.error,portfolio.reconciliation.position_adjusted
TRADING_SYSTEM_WEBHOOK_TIMEOUT=5
TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS=120
TRADING_SYSTEM_RATE_LIMIT_WINDOW_SECONDS=60
```

### Vercel

```
# Required
NEXT_PUBLIC_API_BASE_URL=https://your-service.railway.app/api/v1
```

> The API key is entered at runtime via the frontend UI, not via environment variable.

---

## Rollback

### Railway rollback

1. Railway dashboard → **Deployments** tab.
2. Find the last successful deployment → click **Redeploy**.
3. If an environment variable change caused the issue, restore the previous value first.

### Vercel rollback

1. Vercel dashboard → **Deployments** tab.
2. Find the last successful deployment → **...** → **Promote to Production**.

### Database schema rollback

The Phase 9 migrations use `CREATE TABLE IF NOT EXISTS` so they cannot
be undone by re-running. To roll back the schema entirely:

```sql
-- Warning: destroys all data
DROP TABLE IF EXISTS equity_snapshots;
DROP TABLE IF EXISTS backtest_runs;
```

---

## Deployment Checklist

```
[x] Step 1: Supabase project created
[x] Step 1: Migrations 001 and 002 executed successfully
[x] Step 1: backtest_runs and equity_snapshots tables confirmed
[x] Step 2: Railway repository connected, build succeeded
[x] Step 2: DATABASE_URL and TRADING_SYSTEM_ALLOWED_API_KEYS set
[x] Step 2: GET /health returns 200
[x] Step 2: GET /api/v1/backtests returns 200 (DB connection confirmed)
[x] Step 3: Vercel project created, Root Directory set to "frontend"
[x] Step 3: NEXT_PUBLIC_API_BASE_URL set to Railway URL + /api/v1
[x] Step 3: Vercel deployment succeeded, URL recorded
[x] Step 3: TRADING_SYSTEM_CORS_ALLOW_ORIGINS set in Railway with Vercel URL
[x] Step 4: Frontend loads with API key entered, no errors
[x] Step 4: No CORS errors in browser DevTools
[x] Step 4: SSE heartbeat received via curl (`curl --max-time 20` timeout is expected)
[x] Step 4: Run list preserved after Railway redeploy
[x] Step 4: `run_id` confirmed directly in Supabase `backtest_runs`
```
