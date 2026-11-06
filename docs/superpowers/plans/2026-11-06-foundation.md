# CUT-CLMS Foundation Monorepo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the production-oriented CUT Computer Laboratory Management System monorepo (Turborepo + pnpm + Next.js + FastAPI/uv + PostgreSQL) with tooling, CI, docs, and green validation commands — zero business functionality.

**Architecture:** Single root repo orchestrating JS workspaces (pnpm) and Python services (uv workspace). Next.js apps consume shared TS packages; FastAPI services own config/test tooling per service with one shared `uv.lock`. `services/api` is the single database-schema owner (Alembic). `packages/contracts` holds the canonical OpenAPI commit used to generate the typed `packages/api-client`.

**Tech Stack:** pnpm 12, Turborepo 2, Next.js 16 (App Router, Turbopack), TypeScript 5, Tailwind CSS v4, shadcn-style `packages/ui` (cva/clsx/tailwind-merge), openapi-typescript + openapi-fetch, Python 3.12 + uv 0.13, FastAPI, SQLAlchemy 2 + Alembic + psycopg[binary], ruff + mypy + pytest, Docker Compose (PostgreSQL), GitHub Actions.

**Spec:** The requester's brief in this session (repo layout 1–16, REQUIREMENTS and IMPORTANT lists). Design decisions listed below.

## Global Constraints (from the brief)

- No business functionality implemented anywhere.
- No fake production data, no seed data, no sample records.
- No duplication of business logic across services (currently: no service duplicates another's responsibility; future shared code goes to a shared package per ARCHITECTURE doc).
- Python code distributed per-service; never one monolithic Python app.
- No unnecessary dependencies; every listed dep must have a stated reason.
- Each application/service independently testable (own test runner, own configs).
- Root `pnpm install` and the validation commands must run successfully at completion.

## Design Decisions (locked)

| Decision | Value |
|---|---|
| Repo root | `/home/praisetechzw/cut-clms`, git default branch `main` |
| Node/TS | Node >= 22 (CI uses 24), TypeScript ^5, `"jsx": "preserve"` for Next |
| Package manager | `packageManager: pnpm@12.14.0`, `pnpm-workspace.yaml` |
| Next apps | apps/web :3000 (admin console), apps/portal :3001 (self-service), apps/docs :3002 (docs site) — all Next 16 + Tailwind v4 + Turbopack |
| FastAPI ports | services/api :8000, services/monitoring :8001; endpoint-agent/discovery/deployment/worker are non-HTTP CLI/loop processes |
| Python services | uv workspace root (virtual `pyproject.toml` w/ `[tool.uv.workspace] members = ["services/*"]`), per-service `.venv`, single root `uv.lock` |
| Python stack per service | fastapi+uvicorn (api, monitoring) · pydantic-settings (all) · sqlalchemy+alembic+psycopg[binary] (api only) · httpx runtime (endpoint-agent only) |
| Python tooling per service | ruff (lint+format, line-length 100), mypy (files=["src"], py312), pytest; dev deps only |
| Schema ownership | Only services/api contains Alembic; other services never touch DDL |
| Env vars | Docker: `POSTGRES_*` (root `.env`). Services: `CUT_<SERVICE>_*` via pydantic-settings `env_prefix`. Frontend: `NEXT_PUBLIC_*` |
| Naming | dirs kebab-case; npm packages `@cut-clms/<name>`; Python packages/modules `cut_clms_<name>`; PascalCase TSX components, camelCase utils |
| Turbo tasks | `build` (cached), `dev` (persistent, no cache), `lint`, `typecheck`, `test` (no cache) |
| Python orchestration | each service gets a minimal `package.json` shim whose scripts call uv, so pnpm/turbo fan out uniformly |
| Contracts flow | `services/api` exports `openapi.json` offline via `python -m cut_clms_api.openapi_export` → committed at `packages/contracts/openapi/api.json` → `openapi-typescript` generates `packages/api-client/src/schema.gen.d.ts` |
| Formatting | Prettier (root, single run over repo), ruff format for Python |
| Infra | `infrastructure/docker-compose.yml` with `postgres:17-alpine`, healthcheck, named volume, `.env`-driven |

## File Structure (created by this plan)

```
cut-clms/
├── package.json                 # root scripts (turbo/pnpm engine) + packageManager pin
├── pnpm-workspace.yaml          # apps/*, packages/*, services/*
├── turbo.json                   # tasks: build/dev/lint/typecheck/test
├── tsconfig.base.json           # not used: TS configs live in packages/config
├── .env.example                 # POSTGRES_* + service env examples
├── .editorconfig, .gitignore, .prettierrc.json, .prettierignore
├── README.md                    # comprehensive root README
├── .github/workflows/ci.yml
├── apps/{web,portal,docs}/      # from create-next-app@16, normalized:
│   ├── package.json             # "@cut-clms/web|portal|docs", only scripts dev/build/lint/typecheck/test
│   ├── next.config.ts           # transpilePackages + dev port via script
│   ├── eslint.config.mjs        # extends @cut-clms/config/eslint presets
│   ├── tsconfig.json            # extends @cut-clms/config/tsconfig/next.json
│   ├── app/"page.tsx"/layout/globals.css imported with @cut-clms/ui tokens
│   └── README.md
├── packages/
│   ├── config/                  # @cut-clms/config: eslint (next/base/react) + tsconfig presets
│   ├── ui/                      # @cut-clms/ui: tokens.css, cn(), Button (cva), vitest+RTL test
│   ├── api-client/              # @cut-clms/api-client: schema.gen.d.ts + createApiClient (openapi-fetch), vitest
│   └── contracts/               # @cut-clms/contracts: openapi/api.json (committed), version export, README
├── services/{api,monitoring,discovery,endpoint-agent,deployment,worker}/
│   ├── package.json             # shim: dev/lint/typecheck/test → uv commands
│   ├── pyproject.toml           # uv project + ruff/mypy/pytest config
│   ├── uv.lock                  # (root lockfile only; services share it)
│   ├── src/cut_clms_<name>/     # __init__.py, settings.py, (api: main.py, db.py, openapi_export.py, alembic/)
│   ├── tests/                   # pytest smoke tests
│   └── README.md
├── infrastructure/docker-compose.yml + README.md
├── docs/{architecture.md,dependency-map.md,naming-conventions.md,development.md,decisions/ADR-*.md}
├── scripts/{bootstrap.sh,reset-db.sh,check-openapi-drift.sh}
└── pyproject.toml (root, uv workspace) + uv.lock
```

## Review Focus (failure modes to watch while building)

1. **pnpm v12 build-script gating** — no dependency may need a postinstall build script; keep deps prebuilt/JS-only (watch for pnpm warnings on install).
2. **Tailwind v4 scanning across workspace symlinks** — `packages/ui` classes (cva strings) must be scanned; solved via explicit `@source` in each app's globals.css. Check: compiled CSS contains `.bg-primary`.
3. **Workspace exports/TS resolution through Next builds** — `transpilePackages: ["@cut-clms/ui", "@cut-clms/api-client"]` + correct `exports` maps. Check: `next build` green in web and portal.
4. **uv workspace semantics** — root `uv.lock` shared, per-service venvs; `uv sync --directory services/<x>` works from root.
5. **Alembic with zero migrations** — `alembic upgrade head` must succeed against a fresh DB (creates no tables yet).
6. **OpenAPI drift-check stability** — regenerated JSON must be byte-identical (sorted keys) or CI diff breaks.

---

### Task 0: Repo root hygiene

- [ ] `.gitignore` (node_modules, .next, .turbo, .venv, __pycache__, caches, .env, dist, coverage, uv venvs) — **never ignore `uv.lock`/`pnpm-lock.yaml`**.
- [ ] `.editorconfig`, `.prettierrc.json`, `.prettierignore`.
- [ ] Verify: `ls` shows files, git ignores nothing tracked.

### Task 1: pnpm + Turbo root wiring

- [ ] `package.json` (root): name `cut-clms`, private, `packageManager: pnpm@12.14.0`, engines (node >=22, pnpm >=12), scripts: `dev/build/lint/typecheck/test/format/check/bootstrap/db:up/db:down/db:reset/contracts:generate/contracts:validate`, devDeps: `turbo`, `prettier`, `typescript`.
- [ ] `pnpm-workspace.yaml` with apps/\*, packages/\*, services/\*.
- [ ] `turbo.json` (tasks per Decision table).
- [ ] Install: `pnpm install` → expect lockfile created, no build-script warnings.
- [ ] Commit.

### Task 2: packages/config

- [ ] `@cut-clms/config`: `tsconfig/{base,next,react}.json`, `eslint/{base,react-library,next}.js` flat presets exporting composed arrays, deps: `eslint-config-next`, `@eslint/eslintrc`, `eslint-config-prettier`, `typescript-eslint`, `eslint` + `typescript` devDeps; exports map for both folders.
- [ ] Verify: `pnpm --filter @cut-clms/config test`-able later; smoke: run eslint on an inline copy in Task 7.

### Task 3: packages/ui

- [ ] `@cut-clms/ui`: `src/cn.ts` (`clsx` + `tailwind-merge`), `src/components/button.tsx` (cva variants: default/destructive/outline/secondary/ghost/link; sizes sm/default/lg/icon), `src/index.ts`, `src/styles/tokens.css` (oklch shadcn palette + `@theme inline` mapping), `button.test.tsx` (vitest + @testing-library/react + jsdom).
- [ ] exports: `.` → `src/index.ts`, `./tokens.css` → `src/styles/tokens.css`; peer `react ^19`.
- [ ] Verify: `pnpm --filter @cut-clms/ui test && pnpm --filter @cut-clms/ui lint && pnpm --filter @cut-clms/ui typecheck` green.

### Task 4: services/api (FastAPI core)

- [ ] Shim `package.json` + root uv workspace; `uv add fastapi uvicorn pydantic-settings sqlalchemy alembic 'psycopg[binary]'` and dev `ruff mypy pytest httpx` in `services/api`.
- [ ] `src/cut_clms_api/{__init__,settings,logging,main,db,openapi_export}.py`: settings (`CUT_API_*`, DATABASE_URL default `postgresql+psycopg://cut_clms:cut_clms_dev_password@localhost:5432/cut_clms`), `main.py` with `healthz` + `readyz` (SELECT 1) + operation_ids, `openapi_export.py` (`--output`, sorted keys, version banner), `db.py` (engine factory + `wait_for_db` util), no models (comments only).
- [ ] `alembic.ini` + `alembic/env.py` (sync URL from settings, guarded models import, empty `versions/`).
- [ ] Tests: healthz 200 JSON; `/openapi.json` has both paths; settings prefix; DB module test with SQLite URL smoke.
- [ ] Verify: `uv run --directory services/api pytest -q` + `ruff check` + `ruff format --check` + `mypy` green; `alembic upgrade head` against compose Postgres.

### Task 5: Five remaining Python services (monitoring, discovery, endpoint-agent, deployment, worker)

- [ ] Each: shim `package.json`, `pyproject.toml` (own `CUT_<X>_*` settings; monitoring gets fastapi+uvicorn on :8001 with healthz; others: CLI/loop stubs with `--check` mode, endpoint-agent runtime httpx), `tests/` (settings + importability + entrypoint smoke), uniform ruff/mypy/pytest config.
- [ ] Root `uv lock` → single `uv.lock`; loop `uv run --directory services/<x> pytest` all green.

### Task 6: apps/web, apps/portal, apps/docs

- [ ] `pnpm dlx create-next-app@latest` (offline flags: --ts --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-pnpm --disable-git --skip-install), once each in apps/{web,portal,docs}; then normalize: package name, remove CNA-specific scripts, wire workspace deps (`@cut-clms/ui` in web+portal; `@cut-clms/api-client` type-only import in web), `transpilePackages`, custom pages (foundation placeholder, no business functionality), globals.css importing `@cut-clms/ui/tokens.css` + `@source` for ui sources, port flags (3000/3001/3002), tsconfig/eslint extends from `@cut-clms/config`, `typecheck: tsc --noEmit`, READMEs.
- [ ] Verify: `pnpm turbo run lint typecheck build` all apps green; grep built CSS for `.bg-primary`.

### Task 7: packages/contracts + packages/api-client

- [ ] contracts: generate `openapi/api.json` from api's export module (`pnpm contracts:generate`), package.json exports the JSON; `scripts/check-openapi-drift.sh` regenerates to temp and diffs.
- [ ] api-client: devDep `openapi-typescript`, runDep `openapi-fetch`; `src/index.ts` (`createApiClient` factory typed by `paths`); vitest test with mocked fetch; `generate` script.
- [ ] Verify: `pnpm contracts:generate` idempotent; `pnpm --filter @cut-clms/api-client test` green.

### Task 8: infrastructure + env + scripts

- [ ] `infrastructure/docker-compose.yml`: `postgres:17-alpine` (ports from env, healthcheck `pg_isready`, volume, no init SQL), README.
- [ ] root `.env.example` (+ copy to `.env` in bootstrap only if missing).
- [ ] `scripts/{bootstrap.sh,reset-db.sh,check-openapi-drift.sh}` executable.
- [ ] Verify: `docker compose -f infrastructure/docker-compose.yml config` parses; Postgres starts; `readyz` returns ok; `alembic upgrade head` clean.

### Task 9: CI (GitHub Actions)

- [ ] `.github/workflows/ci.yml`: node job (pnpm install --frozen-lockfile → prettier check → turbo lint/typecheck/build/test), python job (setup-uv → per-service sync/ruff/mypy/pytest), contracts drift job, compose-config job.
- [ ] Verify: YAML parses (python yaml.safe_load).

### Task 10: Docs

- [ ] `docs/{architecture.md,dependency-map.md,naming-conventions.md,development.md}`, `docs/decisions/ADR-000X-*.md` (monorepo split, uv workspaces, api owns schema, contracts pipeline).
- [ ] READMEs: root (comprehensive), every app/package/service/infra dir.
- [ ] Verify: every README reachable, root README commands match reality.

### Task 11: Full validation loop

- [ ] `pnpm install`, `pnpm format`, `pnpm turbo run lint typecheck build test`, `pnpm run check:python` (ruff+mypy+pytest loop), `pnpm contracts:validate`, `docker compose config`.
- [ ] Fix every red until entire loop is green.
- [ ] Final commit.

### Task 12: Completion report

- [ ] List all projects + responsibilities; dependency architecture diagram; exact install/startup commands; summary of checks run and results.
