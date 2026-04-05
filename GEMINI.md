# GEMINI.md - Trading System Workspace Context

> **Source of truth / 기준 문서**
>
> - **EN:** `AGENTS.md` is the primary repository instruction file for workflow, testing expectations, code style, and local skill usage. This file should stay aligned with it, not diverge from it.
> - **KO:** `AGENTS.md`는 워크플로, 테스트 기대치, 코드 스타일, 로컬 스킬 사용에 대한 기본 저장소 지침 문서입니다. 이 문서는 `AGENTS.md`와 정렬되어야 하며, 별도 규칙을 만들지 않아야 합니다.

> **Language policy / 언어 정책**
>
> - **EN:** This document is maintained in both English and Korean. Any future updates must be reflected in **both languages**.
> - **KO:** 이 문서는 영어와 한국어로 유지됩니다. 앞으로의 모든 업데이트는 **두 언어 모두**에 반영되어야 합니다.

---

## 1. Project Overview / 프로젝트 개요

### EN

`trading_system` is a modular Python-based trading workspace designed for both deterministic backtesting and live trading operations. The system is architected with clear service boundaries, emphasizing testability and safe evolution from research to production.

- **Backend:** A Python application built with **FastAPI** serving a REST API for running and managing trading sessions. It uses `uv` for dependency and environment management. The core logic is separated into distinct layers: `data`, `strategy`, `risk`, `execution`, `portfolio`, `backtest`, and `analytics`.
- **Frontend:** A React 19 + TypeScript frontend under `frontend/` is provided for operator-facing workflows. It currently uses Vite 6, TanStack Router, TanStack Query, Zustand, Recharts, and shadcn/ui-style primitives to manage dashboard control, runs, strategies, patterns, and admin surfaces.
- **Configuration:** The system is configured via YAML files (e.g., `configs/base.yaml`) and environment variables, which are parsed and validated by typed settings models.

### KO

`trading_system`은 결정적 백테스팅과 실시간 트레이딩 운영을 모두 지원하도록 설계된 모듈형 Python 기반 트레이딩 워크스페이스입니다. 이 시스템은 명확한 서비스 경계를 갖도록 설계되었으며, 테스트 용이성과 연구에서 운영 환경으로의 안전한 진화를 강조합니다.

- **백엔드:** **FastAPI**로 구축된 Python 애플리케이션으로, 트레이딩 세션을 실행하고 관리하기 위한 REST API를 제공합니다. 의존성 및 환경 관리를 위해 `uv`를 사용합니다. 핵심 로직은 `data`, `strategy`, `risk`, `execution`, `portfolio`, `backtest`, `analytics`와 같은 명확한 레이어로 분리되어 있습니다.
- **프론트엔드:** 운영자용 워크플로를 위한 React 19 + TypeScript 프론트엔드가 `frontend/` 아래에 존재합니다. 현재 Vite 6, TanStack Router, TanStack Query, Zustand, Recharts, shadcn/ui 스타일 프리미티브를 사용하여 대시보드 제어, 실행 이력, 전략, 패턴, 관리 화면을 제공합니다.
- **설정:** 시스템은 YAML 파일(예: `configs/base.yaml`)과 환경 변수를 통해 구성되며, 이는 타입이 지정된 설정 모델에 의해 파싱되고 검증됩니다.

---

## 2. Key Files and Directories / 주요 파일 및 디렉토리

### EN

- `README.md`: The primary entry point for understanding the project, with detailed setup and run commands.
- `pyproject.toml`: Defines project metadata, dependencies (`fastapi`, `uvicorn`, `pytest`), and tool configurations (`ruff`, `pytest`).
- `src/trading_system/`: The main application source code.
  - `app/main.py`: The command-line interface (CLI) entry point for running the trading engine.
  - `api/server.py`: The FastAPI application factory, which sets up middleware, exception handlers, and API routes.
  - `config/settings.py`: Defines the typed data structures for loading and validating application settings from YAML files and environment variables.
  - `app/loop.py`: Contains `LiveTradingLoop` for continuous paper/live trading with graceful shutdown.
  - `backtest/engine.py`: Contains the core logic for orchestrating deterministic backtests.
  - `execution/step.py`: The unified execution core shared by both backtest and live engines.
- `frontend/`: Contains the React/Vite operator-facing frontend.
  - `vite.config.ts`: Vite frontend build configuration.
  - `src/routes/`: TanStack Router route definitions for dashboard, runs, strategies, patterns, and admin pages.
  - `src/api/client.ts`: The TypeScript client for making requests to the backend API.
  - `src/components/`: UI, dashboard, runs, strategies, patterns, and chart components.
  - `src/store/apiStore.ts`: Persisted API base URL/API key state for operator-side API access.
- `tests/`: Contains unit and integration tests, separated by `pytest` markers (`smoke`, `extended`).
- `.github/workflows/tests.yml`: The GitHub Actions workflow for running tests automatically on pull requests and pushes to `main`.
- `scripts/run_engine.sh`: A convenience script for setting up the environment and running the trading engine.

### KO

- `README.md`: 상세한 설정 및 실행 명령어를 포함하여 프로젝트를 이해하기 위한 기본 진입점입니다.
- `pyproject.toml`: 프로젝트 메타데이터, 의존성(`fastapi`, `uvicorn`, `pytest`), 그리고 도구 설정(`ruff`, `pytest`)을 정의합니다.
- `src/trading_system/`: 메인 애플리케이션 소스 코드입니다.
  - `app/main.py`: 트레이딩 엔진을 실행하기 위한 커맨드 라인 인터페이스(CLI) 진입점입니다.
  - `api/server.py`: 미들웨어, 예외 처리기, API 라우트를 설정하는 FastAPI 애플리케이션 팩토리입니다.
  - `config/settings.py`: YAML 파일과 환경 변수로부터 애플리케이션 설정을 로드하고 검증하기 위한 타입이 지정된 데이터 구조를 정의합니다.
  - `app/loop.py`: 안전한 종료 기능을 갖춘 연속적인 페이퍼/라이브 트레이딩을 위한 `LiveTradingLoop`를 포함합니다.
  - `backtest/engine.py`: 결정적 백테스트를 조율하기 위한 핵심 로직을 포함합니다.
  - `execution/step.py`: 백테스트와 라이브 엔진 모두가 공유하는 통합 핵심 실행 로직입니다.
- `frontend/`: React/Vite 기반 운영자용 프론트엔드를 포함합니다.
  - `vite.config.ts`: Vite 프론트엔드 빌드 설정입니다.
  - `src/routes/`: dashboard, runs, strategies, patterns, admin 페이지용 TanStack Router 라우트 정의입니다.
  - `src/api/client.ts`: 백엔드 API에 요청을 보내기 위한 TypeScript 클라이언트입니다.
  - `src/components/`: UI, dashboard, runs, strategies, patterns, 차트 컴포넌트 모음입니다.
  - `src/store/apiStore.ts`: 운영자 측 API base URL/API key 상태를 저장하는 persisted store입니다.
- `tests/`: `pytest` 마커(`smoke`, `extended`)로 분리된 단위 및 통합 테스트를 포함합니다.
- `.github/workflows/tests.yml`: `main` 브랜치에 대한 pull request 및 push 발생 시 자동으로 테스트를 실행하는 GitHub Actions 워크플로우입니다.
- `scripts/run_engine.sh`: 환경을 설정하고 트레이딩 엔진을 실행하기 위한 편의 스크립트입니다.

---

## 3. Building and Running / 빌드 및 실행

### EN

The project uses `uv` for Python environment and package management.

#### 3.1. Initial Setup

To create the virtual environment and install all required dependencies:

```bash
# Create a Python 3.12 virtual environment in .venv
uv venv --python 3.12 --seed .venv

# Install dependencies (including dev dependencies)
uv pip install --python .venv/bin/python -e '.[dev]'
```

#### 3.2. Running Tests

Tests are managed with `pytest` and categorized with markers.

```bash
# Run all tests
uv run --python .venv/bin/python --no-sync pytest

# Run only fast "smoke" tests
uv run --python .venv/bin/python --no-sync pytest -m smoke

# Run extended tests
uv run --python .venv/bin/python --no-sync pytest -m "not smoke"
```

The CI pipeline in `.github/workflows/tests.yml` executes these test sets.

#### 3.3. Running the Application

##### Backend API Server

To serve the FastAPI backend for the frontend or direct API access:

```bash
uv run --python .venv/bin/python --no-sync -m uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000
```

##### Frontend Development Server

To start the frontend dev server:

```bash
cd frontend && npm install && npm run dev
```

The frontend can then be accessed at `http://127.0.0.1:5173/`.

##### Command-Line Interface (CLI)

The application can also be run directly from the command line for backtesting or live pre-flight checks. The `README.md` contains extensive examples.

```bash
# Example backtest run via CLI
uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode backtest --symbols BTCUSDT
```

The `scripts/run_engine.sh` script provides a simpler way to execute these CLI commands.

### KO

이 프로젝트는 Python 환경 및 패키지 관리를 위해 `uv`를 사용합니다.

#### 3.1. 초기 설정

가상 환경을 생성하고 모든 필요한 의존성을 설치하려면 다음을 따르세요:

```bash
# .venv에 Python 3.12 가상 환경 생성
uv venv --python 3.12 --seed .venv

# 의존성 설치 (개발 의존성 포함)
uv pip install --python .venv/bin/python -e '.[dev]'
```

#### 3.2. 테스트 실행

테스트는 `pytest`로 관리되며 마커로 분류됩니다.

```bash
# 모든 테스트 실행
uv run --python .venv/bin/python --no-sync pytest

# 빠른 "smoke" 테스트만 실행
uv run --python .venv/bin/python --no-sync pytest -m smoke

# 확장 테스트 실행
uv run --python .venv/bin/python --no-sync pytest -m "not smoke"
```

`.github/workflows/tests.yml`의 CI 파이프라인이 이 테스트들을 실행합니다.

#### 3.3. 애플리케이션 실행

##### 백엔드 API 서버

프론트엔드나 직접적인 API 접근을 위해 FastAPI 백엔드를 실행합니다:

```bash
uv run --python .venv/bin/python --no-sync -m uvicorn trading_system.api.server:create_app --factory --host 0.0.0.0 --port 8000
```

##### 프론트엔드 개발 서버

프론트엔드 개발 서버를 시작합니다:

```bash
cd frontend && npm install && npm run dev
```

이후 `http://127.0.0.1:5173/`에서 프론트엔드에 접근할 수 있습니다.

##### 커맨드 라인 인터페이스 (CLI)

애플리케이션은 백테스팅이나 라이브 사전 점검을 위해 커맨드 라인에서 직접 실행할 수도 있습니다. `README.md` 파일에 다양한 예시가 포함되어 있습니다.

```bash
# CLI를 통한 백테스트 실행 예시
uv run --python .venv/bin/python --no-sync -m trading_system.app.main --mode backtest --symbols BTCUSDT
```

`scripts/run_engine.sh` 스크립트를 사용하면 이 CLI 명령들을 더 간단하게 실행할 수 있습니다.

---

## 4. Development Conventions / 개발 컨벤션

### EN

- **Architecture:** The codebase is organized into a layered architecture to separate concerns (data, strategy, risk, execution, portfolio, etc.). This is documented in `docs/architecture/overview.md`.
- **Code Style:** Code is formatted and linted using `ruff`. The configuration is in `pyproject.toml`.
- **Configuration:** Application configuration is strictly managed through typed settings classes, loaded from YAML files and environment variables. This provides validation and clarity.
- **API:** The API is versioned (`/api/v1`) and requires an API key for access, which is checked by a custom security middleware (`src/trading_system/api/security.py`).
- **Immutability:** The backtest engine and related components favor an event-driven approach where state changes are recorded as a sequence of immutable events, enhancing observability and determinism.
- **Bilingual Documentation:** The main `README.md` is maintained in both English and Korean.
- **Dashboard Controls:** The live dashboard supports `pause`, `resume`, and `reset` actions via `POST /api/v1/dashboard/control`. `reset` clears EMERGENCY state and returns to PAUSED. See `README.md` §12 for full semantics.
- **Portfolio Risk:** Optional `portfolio_risk` configuration enables drawdown protection (`max_daily_drawdown_pct`), per-position stop-loss (`sl_pct`), and take-profit (`tp_pct`). Documented in `configs/base.yaml`.
- **Agent Workflow:** Follow `AGENTS.md` for repo-local skills and execution workflow. Current local skills include planning/execution skills such as `feature-planner`, `plan-mode-orchestrator`, `build-mode-executor`, `verify-loop-inspector`, plus newer repo-local skills like `frontend-product-designer`, `phase-planner`, and `claude-code-session-handoff`.

### KO

- **아키텍처:** 코드베이스는 관심사를 분리하기 위해 계층적 아키텍처로 구성됩니다 (data, strategy, risk, execution, portfolio 등). 이는 `docs/architecture/overview.md`에 문서화되어 있습니다.
- **코드 스타일:** 코드는 `ruff`를 사용하여 포맷되고 린트됩니다. 설정은 `pyproject.toml`에 있습니다.
- **설정:** 애플리케이션 설정은 YAML 파일과 환경 변수에서 로드되는 타입이 지정된 설정 클래스를 통해 엄격하게 관리됩니다. 이는 유효성 검사와 명확성을 제공합니다.
- **API:** API는 버전이 관리되며(`/api/v1`), 접근 시 API 키가 필요합니다. 이는 커스텀 보안 미들웨어(`src/trading_system/api/security.py`)에 의해 확인됩니다.
- **불변성:** 백테스트 엔진 및 관련 구성 요소는 상태 변경이 불변 이벤트의 시퀀스로 기록되는 이벤트 기반 접근 방식을 선호하여 관측성과 결정성을 향상시킵니다.
- **이중 언어 문서:** 주요 `README.md`는 영어와 한국어로 모두 유지 관리됩니다.
- **대시보드 제어:** 라이브 대시보드는 `POST /api/v1/dashboard/control`을 통해 `pause`, `resume`, `reset` 액션을 지원합니다. `reset`은 EMERGENCY 상태를 해제하고 PAUSED로 복귀합니다. 전체 의미는 `README.md` §12를 참조하세요.
- **포트폴리오 리스크:** 선택적 `portfolio_risk` 설정으로 드로우다운 보호(`max_daily_drawdown_pct`), 포지션별 손절(`sl_pct`), 익절(`tp_pct`)을 활성화할 수 있습니다. `configs/base.yaml`에 문서화되어 있습니다.
- **에이전트 워크플로:** repo-local skill과 실행 워크플로는 `AGENTS.md`를 따릅니다. 현재 로컬 스킬에는 `feature-planner`, `plan-mode-orchestrator`, `build-mode-executor`, `verify-loop-inspector` 같은 계획/실행 스킬과, 새로 추가된 `frontend-product-designer`, `phase-planner`, `claude-code-session-handoff`가 포함됩니다.
