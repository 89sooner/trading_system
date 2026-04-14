# 운영 배포 절차 — Supabase · Railway · Vercel

## 목적

이 문서는 Phase 9에서 구성한 인프라 스택을 기반으로,
트레이딩 시스템을 처음 운영 환경에 배포하는 전체 절차를 단계별로 기술한다.

- **Supabase** — PostgreSQL 데이터베이스 (런 영속화, equity 시계열)
- **Railway** — FastAPI 백엔드 서버 (SSE 스트리밍 포함 모든 API)
- **Vercel** — Next.js 프론트엔드

이 문서는 순서대로 진행해야 한다.
각 단계에는 완료 판단 기준(Exit criteria)이 포함되어 있으며,
검증을 건너뛰면 이후 단계에서 원인 추적이 어려워진다.

---

## 사전 준비

### 필요한 계정

| 서비스 | 용도 | URL |
|--------|------|-----|
| Supabase | PostgreSQL DB | https://supabase.com |
| Railway | FastAPI 백엔드 호스팅 | https://railway.app |
| Vercel | Next.js 프론트엔드 호스팅 | https://vercel.com |
| GitHub | 소스 코드 리포지토리 | https://github.com |

### 필요한 로컬 도구

```bash
# 설치 여부 확인
psql --version        # PostgreSQL 클라이언트 (마이그레이션 실행용)
git --version
node --version        # 18 이상
```

`psql`이 없으면 Supabase 대시보드 SQL Editor를 대신 사용할 수 있다.

### 코드베이스 상태 확인

```bash
# main 브랜치 최신 상태 확인
git status
git log --oneline -5

# 로컬 테스트 통과 확인
pytest --tb=short -q
ruff check src/ tests/
```

로컬 테스트가 통과한 상태에서만 배포를 시작한다.

---

## 1단계. Supabase — 데이터베이스 설정

### 1-1. 프로젝트 생성

1. https://supabase.com 에 로그인한다.
2. **New project** 를 클릭한다.
3. 아래 항목을 입력한다:
   - **Name**: `trading-system` (원하는 이름)
   - **Database Password**: 강력한 패스워드를 생성하고 **반드시 기록해 둔다**.
     이 패스워드는 이후 `DATABASE_URL`에 포함된다.
   - **Region**: 사용자 위치와 가까운 리전 선택 (예: `Northeast Asia (Seoul)`)
4. **Create new project** 를 클릭하고 프로젝트가 준비될 때까지 대기한다 (약 1~2분).

### 1-2. Connection String 복사

1. 좌측 메뉴 → **Project Settings** → **Database** 탭 진입.
2. **Connection string** 섹션에서 **URI** 탭 선택.
3. `postgresql://postgres:[YOUR-PASSWORD]@db.[ref].supabase.co:5432/postgres` 형식의 문자열을 복사한다.
4. `[YOUR-PASSWORD]` 부분을 1-1에서 설정한 패스워드로 교체한다.
5. 이 값이 `DATABASE_URL`이다. 메모장 등 임시 저장소에 보관한다.

> **보안 주의**: `DATABASE_URL`은 절대 커밋하지 않는다. `.env.example`을 참고해 `.env` 파일에만 저장한다.

### 1-3. 스키마 마이그레이션 실행

```bash
# 저장소 루트에서 실행
export DATABASE_URL="postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres"

psql "$DATABASE_URL" -f scripts/migrations/001_create_backtest_runs.sql
psql "$DATABASE_URL" -f scripts/migrations/002_create_equity_snapshots.sql
```

`psql`을 사용할 수 없는 경우 **Supabase 대시보드 SQL Editor** 에서 직접 실행한다:
1. 좌측 메뉴 → **SQL Editor** → **New query**.
2. `scripts/migrations/001_create_backtest_runs.sql` 내용을 붙여 넣고 **Run** 클릭.
3. 동일하게 `002_create_equity_snapshots.sql` 실행.

### 1-4. 테이블 생성 확인

Supabase 대시보드 → **Table Editor** 에서 다음 두 테이블이 보여야 한다:
- `backtest_runs`
- `equity_snapshots`

또는 SQL Editor에서 확인:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';
```

**Exit criteria**: `backtest_runs`, `equity_snapshots` 테이블이 존재하고, `equity_snapshots`에 `idx_equity_snapshots_session_ts` 인덱스가 생성되어 있다.

---

## 2단계. Railway — FastAPI 백엔드 배포

### 2-1. 프로젝트 생성 및 리포지토리 연결

1. https://railway.app 에 로그인한다.
2. **New Project** → **Deploy from GitHub repo** 선택.
3. GitHub 계정을 연결하고 이 리포지토리를 선택한다.
4. Railway가 배포 방식을 자동 선택해 빌드를 시작한다.
   - `Dockerfile`이 감지되면 Docker 기반으로 빌드될 수 있다.
   - 서비스가 `Railpack`(Python + `uv`)으로 잡히는 경우도 있다.
   - 빌드가 완료될 때까지 기다리지 않고, 바로 환경변수 설정으로 진행한다.
5. 서비스가 `Railpack`으로 배포되는 경우 **Settings** 또는 **Deploy** 설정에서
   **Start Command** 를 아래 값으로 직접 입력한다.

```bash
uv run --no-sync -m uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port $PORT
```

6. `Railpack`을 사용하는 경우 빌드 단계에서 `uv sync --locked`가 실행되므로,
   `pyproject.toml`을 수정했다면 반드시 로컬에서 `uv lock`을 다시 실행한 뒤
   갱신된 `uv.lock`까지 함께 커밋/푸시해야 한다.

```bash
UV_CACHE_DIR=.uv-cache uv lock
git add pyproject.toml uv.lock
git commit -m "Update uv lockfile"
git push
```

### 2-2. 환경변수 설정

Railway 대시보드 → 생성된 서비스 → **Variables** 탭에서 아래 항목을 입력한다.

#### 필수

| 변수명 | 값 | 설명 |
|--------|-----|------|
| `DATABASE_URL` | `postgresql://postgres:[pw]@db.[ref].supabase.co:5432/postgres` | Supabase Connection String |
| `TRADING_SYSTEM_ALLOWED_API_KEYS` | `your-secret-api-key` | API 인증 키. 쉼표로 여러 개 지정 가능 |

> `TRADING_SYSTEM_ALLOWED_API_KEYS` 값은 Vercel 프론트엔드에서 입력할 API key와 동일해야 한다.
> 예: `TS-PROD-KEY-A1B2C3D4` — 충분히 긴 무작위 문자열을 사용한다.

#### 선택 (권장)

| 변수명 | 값 예시 | 설명 |
|--------|---------|------|
| `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` | *(Vercel 배포 후 설정, 3단계 참고)* | CORS 허용 오리진 |
| `TRADING_SYSTEM_WEBHOOK_URL` | `https://hooks.example.com/trading` | Webhook 알림 URL (미설정 시 비활성) |
| `TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS` | `120` | 분당 요청 제한 (기본 60) |

> `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`는 Vercel 배포 URL을 얻은 뒤 **3-4 단계**에서 추가한다.

### 2-3. 배포 완료 및 URL 확인

1. Railway 대시보드 → **Deployments** 탭에서 빌드 로그 확인.
2. 빌드 성공 후 **Settings** → **Domains** 에서 자동 생성된 URL을 확인한다.
   형태: `https://your-service.railway.app`
3. 이 URL을 메모해 둔다 (Vercel 환경변수에 사용).

### 2-4. 헬스체크 확인

```bash
RAILWAY_URL="https://your-service.railway.app"
curl -s "$RAILWAY_URL/health"
# 기대 응답: {"status": "ok"}
```

### 2-5. API 동작 확인

```bash
API_KEY="your-secret-api-key"

# 백테스트 런 목록 (빈 목록이어도 200 응답이면 DB 연결 성공)
curl -s -H "X-API-Key: $API_KEY" "$RAILWAY_URL/api/v1/backtests"
# 기대 응답: {"runs": [], "total": 0, "page": 1, "page_size": 20}
```

**Exit criteria**: `/health` 200 응답, `/api/v1/backtests` 200 응답 (DB 연결 성공 확인).

---

## 3단계. Vercel — 프론트엔드 배포

### 3-1. 프로젝트 생성 및 리포지토리 연결

1. https://vercel.com 에 로그인한다.
2. **New Project** → GitHub 리포지토리 import.
3. **Configure Project** 화면에서:
   - **Root Directory**: `frontend` 로 변경 (필수).
   - **Framework Preset**: `Next.js` 자동 감지됨.
   - Build Command, Output Directory는 기본값 유지.

### 3-2. 환경변수 설정

**Configure Project** 화면의 **Environment Variables** 섹션에서 입력한다.

| 변수명 | 값 | 설명 |
|--------|-----|------|
| `NEXT_PUBLIC_API_BASE_URL` | `https://your-service.railway.app/api/v1` | Railway 백엔드 URL + `/api/v1` (슬래시로 끝나지 않게) |

> API key는 환경변수로 주입하지 않는다.
> 프론트엔드 우측 상단의 API key 입력 UI에서 런타임에 입력한다.

### 3-3. 배포 실행

**Deploy** 버튼을 클릭하고 빌드 로그를 확인한다.
배포 성공 후 Vercel이 제공하는 URL을 기록한다.
형태: `https://your-app.vercel.app`

### 3-4. Railway CORS 설정 추가

Vercel 배포 URL을 Railway의 CORS 허용 오리진에 추가한다.

Railway 대시보드 → 서비스 → **Variables** 탭:

| 변수명 | 값 |
|--------|-----|
| `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` | `https://your-app.vercel.app` |

> 쉼표로 여러 도메인을 지정할 수 있다: `https://your-app.vercel.app,https://custom-domain.com`
> 값 끝에 슬래시(`/`)를 붙이지 않는다 — CORS 비교는 정확히 일치 방식이다.

환경변수 추가 후 Railway가 자동으로 재배포한다. 재배포 완료까지 대기한다.

---

## 4단계. 통합 검증

### 4-1. 프론트엔드 → 백엔드 API 연동

1. Vercel URL로 프론트엔드에 접속한다.
2. 우측 상단 설정 아이콘 → API Key 입력란에 `TRADING_SYSTEM_ALLOWED_API_KEYS` 값 입력.
3. 대시보드 페이지가 오류 없이 로드되는지 확인한다.
4. 브라우저 개발자 도구 → **Network** 탭에서 CORS 오류(`blocked by CORS policy`)가 없는지 확인한다.

### 4-2. SSE 스트리밍 연결

```bash
API_KEY="your-secret-api-key"
RAILWAY_URL="https://your-service.railway.app"

# SSE 연결 확인 (15초 이내 heartbeat 수신)
curl -N -H "Accept: text/event-stream" \
  "$RAILWAY_URL/api/v1/dashboard/stream?api_key=$API_KEY"

# 기대 출력 (15초 간격):
# event: heartbeat
# data: {}
#
# ^C 로 종료
```

### 4-3. 백테스트 런 영속화 확인

1. 프론트엔드에서 백테스트를 한 번 실행한다.
2. `/runs` 페이지에서 방금 실행한 런이 목록에 보이는지 확인한다.
3. Railway 대시보드 → **Redeploy** 로 서비스를 재시작한다.
4. 재시작 후 `/runs` 페이지를 새로고침하여 런이 여전히 남아있는지 확인한다.
   - 남아있으면 Supabase DB 영속화 성공.
   - 사라지면 `DATABASE_URL` 연결 오류이므로 Railway 로그 확인.

### 4-4. Supabase 데이터 직접 확인

```bash
psql "$DATABASE_URL" -c "SELECT run_id, status, started_at FROM backtest_runs ORDER BY created_at DESC LIMIT 5;"
```

**Exit criteria 요약**:

| 항목 | 기준 |
|------|------|
| `GET /health` | 200 `{"status": "ok"}` |
| `GET /api/v1/backtests` | 200, CORS 오류 없음 |
| SSE `/dashboard/stream` | heartbeat 수신 |
| 재배포 후 런 목록 | 이전 런 보존 |
| 브라우저 CORS | 오류 없음 |

---

## 5단계. 커스텀 도메인 연결 (선택)

### Vercel 커스텀 도메인

1. Vercel 대시보드 → **Settings** → **Domains** → 도메인 추가.
2. 도메인 제공업체에서 CNAME 또는 A 레코드를 설정한다.
3. Vercel에서 SSL 인증서가 자동 발급된다.

### Railway 커스텀 도메인

1. Railway 대시보드 → 서비스 → **Settings** → **Domains** → 커스텀 도메인 추가.
2. DNS CNAME 레코드 설정.
3. CORS 오리진을 새 도메인으로 업데이트한다.

---

## 문제 해결

### Railway 배포 실패

**증상**: 빌드 로그에 오류가 보인다.

```bash
# 자주 발생하는 원인 확인
# 1. pyproject.toml 의존성 설치 오류
#    → psycopg[binary] 버전 확인
# 2. COPY 대상 파일 누락
#    → uv.lock 파일이 있으면 Dockerfile이 복사하므로 확인
# 3. Railpack + uv sync --locked 실패
#    → pyproject.toml 변경 후 uv.lock 미갱신 여부 확인
# 4. Railpack Start Command 미설정
#    → "No start command detected" 로그 확인
```

**해결**: Railway 대시보드 → **Deployments** → 실패한 배포의 **View Logs** 에서 오류 메시지 확인.

추가 체크:
1. 로그에 `Railpack`이 보이면 Dockerfile이 아니라 Railpack 배포로 실행 중인 것이다.
2. `No start command detected`가 보이면 Start Command를 아래 값으로 설정한다.

```bash
uv run --no-sync -m uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port $PORT
```

3. `The lockfile at uv.lock needs to be updated, but --locked was provided`가 보이면
   로컬에서 아래 명령으로 lockfile을 갱신한 뒤 `uv.lock`까지 커밋/푸시한다.

```bash
UV_CACHE_DIR=.uv-cache uv lock
git add pyproject.toml uv.lock
git commit -m "Update uv lockfile"
git push
```

4. 배포는 성공했지만 시작 직후 `ModuleNotFoundError: No module named 'httpx'`로 크래시하면
   `httpx`가 개발 전용 의존성(`dev`)에만 있고 운영 의존성(`dependencies`)에 빠진 상태일 수 있다.
   이 경우 `pyproject.toml`에서 `httpx`를 runtime dependency로 옮기고 `uv.lock`을 다시 갱신한다.

```bash
UV_CACHE_DIR=.uv-cache uv lock
git add pyproject.toml uv.lock
git commit -m "Move httpx to runtime dependencies"
git push
```

---

### `GET /health` 502 오류

**증상**: 헬스체크 요청이 502 또는 timeout 반환.

**원인 및 해결**:
1. 빌드는 성공했지만 컨테이너 시작 실패 → Railway 로그에서 `uvicorn` 실행 오류 확인.
2. `DATABASE_URL` 연결 실패 → `psycopg.connect()` 오류가 로그에 출력됨. Supabase Connection String 재확인.
3. `$PORT` 미할당 → Railway는 자동으로 `PORT` 환경변수를 주입하며 Dockerfile CMD가 `${PORT:-8000}`을 사용하므로 문제없음.
4. `ModuleNotFoundError: No module named 'httpx'` → webhook 모듈이 import되지만 `httpx`가 production install에 빠진 상태. `pyproject.toml` runtime dependencies와 `uv.lock`를 함께 갱신 후 재배포.

---

### CORS 오류 (`blocked by CORS policy`)

**증상**: 브라우저 콘솔에 CORS 오류가 보인다.

**체크리스트**:
1. Railway의 `TRADING_SYSTEM_CORS_ALLOW_ORIGINS` 값이 정확한지 확인.
   - 올바른 형식: `https://your-app.vercel.app` (끝에 `/` 없음)
   - 잘못된 형식: `https://your-app.vercel.app/` ← 슬래시 제거
2. Railway 환경변수 수정 후 재배포가 완료됐는지 확인.
3. Vercel의 `NEXT_PUBLIC_API_BASE_URL`에 `/api/v1`가 포함되어 있는지 확인.

---

### 백테스트 런 목록이 재배포 후 사라짐

**증상**: Railway 재배포 후 `/runs` 목록이 비어있다.

**원인**: `DATABASE_URL`이 설정되지 않아 파일 기반(`data/runs/`)으로 동작하고 있는 것.
컨테이너 재시작 시 파일이 초기화된다.

**해결**:
1. Railway 서비스의 `DATABASE_URL` 환경변수가 정확히 설정되어 있는지 확인.
2. Railway 로그에서 서버 시작 시 `psycopg.connect()` 오류가 없는지 확인.
3. 환경변수 수정 후 **Redeploy**.

---

### SSE 연결이 즉시 끊긴다

**증상**: `curl -N` 이 즉시 종료되거나 `data: {"error":...}` 반환.

**체크리스트**:
1. `api_key` 쿼리 파라미터가 정확한지 확인.
2. Railway의 `/health` 가 정상이면 서버 자체는 살아있음.
3. Railway 로그에서 `SSE stream` 관련 오류 확인.

---

## 환경변수 전체 참조

### Railway 환경변수

```
# 필수
DATABASE_URL=postgresql://postgres:[pw]@db.[ref].supabase.co:5432/postgres
TRADING_SYSTEM_ALLOWED_API_KEYS=your-secret-api-key

# CORS — Vercel 배포 URL (3단계 후 추가)
TRADING_SYSTEM_CORS_ALLOW_ORIGINS=https://your-app.vercel.app

# 선택
TRADING_SYSTEM_WEBHOOK_URL=
TRADING_SYSTEM_RATE_LIMIT_MAX_REQUESTS=120
TRADING_SYSTEM_RATE_LIMIT_WINDOW_SECONDS=60
```

### Vercel 환경변수

```
# 필수
NEXT_PUBLIC_API_BASE_URL=https://your-service.railway.app/api/v1
```

> API key는 Vercel 환경변수로 설정하지 않는다.
> 프론트엔드 UI에서 런타임 입력 방식을 유지한다.

---

## 롤백 절차

### Railway 롤백

1. Railway 대시보드 → **Deployments** 탭.
2. 이전 성공한 배포 항목 → **Redeploy** 클릭.
3. 환경변수 변경이 원인이면 변경 전 값으로 복원 후 재배포.

### Vercel 롤백

1. Vercel 대시보드 → **Deployments** 탭.
2. 이전 성공한 배포 항목 → **...** → **Promote to Production** 클릭.

### DB 스키마 롤백

스키마 변경이 필요한 경우에만 해당한다. Phase 9의 마이그레이션은 `CREATE TABLE IF NOT EXISTS` 이므로 단순히 실행을 취소할 수 없다. 롤백이 필요하면 수동으로 테이블을 삭제한다:

```sql
-- 주의: 모든 데이터가 삭제된다
DROP TABLE IF EXISTS equity_snapshots;
DROP TABLE IF EXISTS backtest_runs;
```

---

## 배포 완료 체크리스트

```
[ ] 1단계: Supabase 프로젝트 생성 완료
[ ] 1단계: SQL 마이그레이션 2개 실행 완료 (001, 002)
[ ] 1단계: backtest_runs, equity_snapshots 테이블 생성 확인
[ ] 2단계: Railway 리포지토리 연결 및 빌드 성공
[ ] 2단계: DATABASE_URL, TRADING_SYSTEM_ALLOWED_API_KEYS 환경변수 설정
[ ] 2단계: GET /health 200 응답 확인
[ ] 2단계: GET /api/v1/backtests 200 응답 확인 (DB 연결 확인)
[ ] 3단계: Vercel 프로젝트 생성, Root Directory = frontend 설정
[ ] 3단계: NEXT_PUBLIC_API_BASE_URL 환경변수 설정
[ ] 3단계: Vercel 배포 성공 및 URL 확인
[ ] 3단계: Railway TRADING_SYSTEM_CORS_ALLOW_ORIGINS에 Vercel URL 추가
[ ] 4단계: 프론트엔드에서 API key 입력 후 대시보드 로드 확인
[ ] 4단계: CORS 오류 없음 확인 (브라우저 개발자 도구)
[ ] 4단계: SSE heartbeat 수신 확인
[ ] 4단계: 백테스트 실행 → 재배포 후 런 목록 보존 확인
```
