# Phase 9 Plan Review From Codex

## Findings

### 1. High: `build_services()` 분기만으로는 백테스트 런 영속화가 Supabase로 전환되지 않는다

관련 문서:
- `prd/phase_9_prd.md:67-76`
- `prd/phase_9_prd.md:133-137`
- `prd/phase_9_implementation_plan.md:14-18`
- `prd/phase_9_implementation_plan.md:86-102`
- `prd/phase_9_task.md:101-115`

현재 코드 근거:
- `src/trading_system/api/routes/backtest.py:40-42`
- `src/trading_system/api/routes/backtest.py:180-230`
- `src/trading_system/api/routes/analytics.py`
- `tests/unit/test_api_server.py:7-9`
- `tests/integration/test_run_persistence_integration.py:24-30`

문제:
- 문서는 `DATABASE_URL` 존재 시 `build_services()`가 `SupabaseBacktestRunRepository`를 선택하면 런 저장소가 교체된다고 가정한다.
- 하지만 실제 `/api/v1/backtests`, `/api/v1/backtests/{run_id}`, analytics 조회는 `build_services()`를 통하지 않고 모듈 전역 `_RUN_REPOSITORY`를 직접 사용한다.
- 현재 `create_backtest_run()`은 `services.run()`으로 백테스트를 실행한 뒤 결과 저장은 `_RUN_REPOSITORY.save(...)`로 별도 수행한다.
- 따라서 문서대로 Step 9-4만 구현하면 실행 경로와 조회 경로는 계속 파일 저장소를 사용하고, PRD의 핵심 목표인 “컨테이너 재배포 후 런 보존”이 달성되지 않는다.

권장 수정:
- Phase 9의 저장소 전환 책임을 `build_services()`가 아니라 “API 라우트가 참조하는 런 저장소 조립 경로”까지 포함하도록 다시 정의한다.
- `api/routes/backtest.py`와 `api/routes/analytics.py`를 impacted files에 추가하고, `_RUN_REPOSITORY` 초기화 방식을 env-aware factory 또는 app-state dependency로 바꾸는 항목을 명시한다.
- 테스트 계획에도 `_RUN_REPOSITORY` 교체에 영향을 받는 API/통합 테스트 갱신을 포함해야 한다.

### 2. High: `EquityWriter` 추상화 설계가 현재 런타임 계약을 완전히 반영하지 않아 타입 분리 후 바로 깨질 수 있다

관련 문서:
- `prd/phase_9_prd.md:19`
- `prd/phase_9_prd.md:126-131`
- `prd/phase_9_implementation_plan.md:36-39`
- `prd/phase_9_implementation_plan.md:60-76`
- `prd/phase_9_task.md:23-27`
- `prd/phase_9_task.md:81-97`

현재 코드 근거:
- `src/trading_system/app/loop.py:8`
- `src/trading_system/app/loop.py:27-40`
- `src/trading_system/api/routes/dashboard.py:172-193`
- `src/trading_system/app/equity_writer.py:8-30`

문제:
- 문서는 `EquityWriter` 인터페이스를 `append()`와 `read_recent()` 두 메서드만 가진 것으로 적고 있다.
- 하지만 실제 API는 `/api/v1/dashboard/equity` 응답에서 `equity_writer.session_id` 속성도 읽는다.
- 또한 현재 `LiveTradingLoop`는 `equity_writer: EquityWriter | None` 필드를 직접 들고 있고, `AppServices`에는 `equity_writer` 필드가 없다.
- 구현 계획은 `AppServices`에 `equity_writer`를 추가한다고 적었지만, 실제로 어디서 `LiveTradingLoop.equity_writer`에 주입되는지, live loop 생성 시 어떤 `session_id`를 쓸지, live 재시작 시 세션 정책을 어떻게 유지할지 정의하지 않았다.

권장 수정:
- `EquityWriterProtocol`에 `session_id` 읽기 계약을 명시하거나, 대시보드 DTO가 `session_id` 없이도 동작하도록 API 계약을 다시 정의한다.
- `build_services()`가 아닌 `LiveTradingLoop` 생성 경로까지 포함해 “writer 생성 → loop 주입 → dashboard 조회”의 전체 경로를 문서에 고정해야 한다.
- `session_id` 생성 정책을 명시한다.
  새 live-loop마다 새 세션을 만들지, 프로세스 생애주기 단위로 고정할지 결정이 필요하다.

### 3. High: CORS 계획이 현재 보안 미들웨어 구조 및 실제 env var 이름과 충돌한다

관련 문서:
- `prd/phase_9_prd.md:100-104`
- `prd/phase_9_prd.md:145-151`
- `prd/phase_9_implementation_plan.md:52-56`
- `prd/phase_9_implementation_plan.md:239-263`
- `prd/phase_9_task.md:103-112`

현재 코드 근거:
- `src/trading_system/api/security.py:17-38`
- `src/trading_system/api/security.py:75-80`
- `src/trading_system/api/server.py:40-41`
- `src/trading_system/config/settings.py:64`
- `configs/base.yaml:27-31`
- `.env.example:16-19`

문제:
- 문서는 `TRADING_SYSTEM_CORS_ORIGINS`와 `server.py`의 `CORSMiddleware`를 전제로 하지만, 현재 시스템은 `CORSMiddleware`를 쓰지 않고 자체 security middleware에서 CORS 헤더를 직접 붙인다.
- 현재 env var 이름도 `TRADING_SYSTEM_CORS_ORIGINS`가 아니라 `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`다.
- PRD는 `configs/base.yaml`이 localhost만 허용한다고 적었지만 실제 기본값은 `*`다.
- 이 상태에서 문서대로 `CORSMiddleware`를 추가하면 기존 security middleware의 CORS 처리와 중복될 수 있고, OPTIONS 처리나 허용 헤더 동작이 이원화될 위험이 있다.

권장 수정:
- 먼저 “기존 security middleware 기반 CORS를 유지할지, FastAPI `CORSMiddleware`로 일원화할지”를 결정사항으로 고정한다.
- env var 이름은 현재 운영 문서와 코드에 맞춰 `TRADING_SYSTEM_CORS_ALLOW_ORIGINS`를 유지하거나, Phase 9에서 rename migration을 명시적으로 수행해야 한다.
- PRD의 baseline 설명도 `configs/base.yaml` 현재값과 맞게 수정해야 한다.

### 4. Medium: 프론트엔드 배포 계획이 현재 `NEXT_PUBLIC_API_BASE_URL` + runtime override 구조를 잘못 이해하고 있다

관련 문서:
- `prd/phase_9_prd.md:39`
- `prd/phase_9_prd.md:153-158`
- `prd/phase_9_implementation_plan.md:343-387`
- `prd/phase_9_task.md:143-160`

현재 코드 근거:
- `frontend/store/apiStore.ts:4-27`
- `frontend/lib/api/client.ts:19-30`
- `frontend/lib/api/dashboard.ts:22-27`
- `frontend/README.md:18-32`
- `frontend/.env.local.example`

문제:
- 문서는 프론트가 `NEXT_PUBLIC_API_URL`을 사용한다고 적지만, 실제 기본 env var는 `NEXT_PUBLIC_API_BASE_URL`이고 값에도 `/api/v1` prefix가 포함된다.
- API key도 `NEXT_PUBLIC_API_KEY`에서 읽지 않고, Zustand store에 운영자가 런타임에 입력하는 구조다.
- 이 구조는 이미 frontend README와 `.env.local.example`에 문서화되어 있다.
- 문서대로 `NEXT_PUBLIC_API_URL`과 `NEXT_PUBLIC_API_KEY`를 새 표준으로 도입하면, 기존 operator override UX를 유지할지 제거할지 결정 없이 env 체계가 이중화된다.

권장 수정:
- Phase 7에서 고정한 방향대로 env var는 기본 base URL만 제공하고, operator override UI는 유지할지 여부를 먼저 확정한다.
- 유지한다면 Phase 9는 `NEXT_PUBLIC_API_BASE_URL`을 Vercel 기본값으로 세팅하는 수준으로 충분하며, `NEXT_PUBLIC_API_KEY`는 필수가 아니라 “optional seeded default”인지 여부를 명시해야 한다.
- impacted files에 `frontend/store/apiStore.ts`, `frontend/README.md`, `frontend/.env.local.example` 또는 교체 대상 env example 파일을 명시하는 편이 안전하다.

### 5. Medium: 배포/문서 단계가 현재 저장소의 실제 엔트리포인트와 문서 정책을 충분히 반영하지 않는다

관련 문서:
- `prd/phase_9_prd.md:84-90`
- `prd/phase_9_prd.md:139-145`
- `prd/phase_9_prd.md:160-164`
- `prd/phase_9_implementation_plan.md:41-45`
- `prd/phase_9_implementation_plan.md:271-339`
- `prd/phase_9_task.md:119-139`
- `README.md:1-8`

현재 코드 근거:
- `src/trading_system/api/server.py:24-82`
- `.env.example:1-61`
- `README.md:1-8`

문제:
- Docker 예시는 `uvicorn trading_system.api.server:app`를 사용하지만, 현재 `server.py`에는 모듈 전역 `app`이 없고 `create_app()`만 있다.
- 따라서 문서대로 Dockerfile을 쓰면 컨테이너 기동 단계에서 바로 실패한다.
- 또 `.env.example`은 이미 존재하는 파일인데 계획은 이를 신규 생성처럼 취급한다.
- README는 영어/한국어 동시 업데이트가 강제되어 있는데, 계획은 배포 문서 보강 시 이 저장소 규칙을 명시하지 않는다.

권장 수정:
- 배포 엔트리포인트를 먼저 고정한다.
  예: `app = create_app()`를 모듈 전역에 추가하거나, uvicorn factory 모드(`--factory`)를 사용한다.
- `.env.example`은 신규 생성이 아니라 “기존 템플릿 확장 및 env name migration”으로 기술해야 한다.
- README 배포 섹션 작업에는 bilingual update requirement를 명시해야 한다.

## Overall Assessment

방향 자체는 맞다.

- Supabase로 런/에쿼티 영속화를 옮기고 Railway/Vercel로 배포한다는 큰 축은 현재 시스템의 다음 단계로 자연스럽다.
- 파일 기반 구현을 완전히 제거하지 않고 로컬 fallback을 남기려는 원칙도 저장소 성격과 잘 맞는다.
- CI, 배포 설정, 문서화까지 한 phase에 묶은 것도 운영 전환 관점에서는 타당하다.

다만 현재 문서는 “바로 구현 시작 가능한 수준”은 아니다.

- 가장 큰 문제는 저장소 전환 책임이 실제 코드 경로와 어긋나 있다는 점이다.
- 그 다음으로 `EquityWriter` 계약, CORS 처리 방식, 프론트 env 체계가 현재 코드와 충돌한다.
- 배포 단계 역시 uvicorn 엔트리포인트와 기존 문서 자산을 정확히 반영하지 못한다.

즉, 지금 상태에서 구현을 시작하면 일부 slice는 문서대로 완료해도 실제 목표를 달성하지 못할 가능성이 높다.

## Recommendation

추천 판단은 다음과 같다.

1. 이 계획은 폐기할 필요는 없다.
2. 하지만 구현 전 `phase_9_prd.md`, `phase_9_implementation_plan.md`, `phase_9_task.md`를 한 번 더 보정해야 한다.
3. 우선순위는 다음 순서가 안전하다.
   - 런 저장소 전환 경로를 `_RUN_REPOSITORY` 중심으로 다시 정의
   - `EquityWriter` 전체 계약과 live-loop 주입 경로 확정
   - CORS 단일 구현 방식과 env var 이름 확정
   - 프론트 env 전략을 `NEXT_PUBLIC_API_BASE_URL` 기준으로 정리
   - Docker/README/.env.example 단계의 실제 엔트리포인트와 문서 정책 반영

이 다섯 가지가 반영되면 Phase 9는 구현 착수 가능한 수준으로 올라간다.
