# Repo-Aware Chat + Continual Learning Engine — Product Brief

## 1) What it is (product)

A **web app** where you connect a GitHub repo and get a **repo-aware chat** that:

- Answers with **file:line citations** and code previews.
- Stays fresh via **diff indexing** on pushes/PRs.
- When **Continual Learning** is ON, a background engine “thinks forever” about the repo: mapping risks, hypothesizing bugs, generating/verifying tests, profiling hot spots, and drafting safe PRs—feeding all findings back into chat and the UI.

## 2) Users & value

- **Developers/teams**: instant codebase understanding, safe auto-insights, fewer regressions.
- **Leads**: living risk map, change summaries, evidence-backed recommendations.
- **Enterprises**: private tenant, optional on-prem, per-repo adapters later.

## 3) Architecture (Python + Go microservices)

```
[Next.js/React/TS] ─► [API Gateway]
      │
      ├─► Python “Brain” (FastAPI)
      │     • Chat (LLM + RAG + citations)
      │     • Reranker & prompt policy
      │     • Summarizers, test synthesis
      │
      ├─► Go “Thinker” Workers
      │     • Webhook handler, schedulers
      │     • Clone/diff, parse, embed
      │     • Static/dynamic checks, fuzz, bench
      │     • PR draft (never auto-merge)
      │
      └─► Stores
            • Postgres (+ pgvector)
            • Object storage (artifacts)
            • Queue (Redis/NATS)
```

**Why this split:** Python = LLM/ML ecosystem; Go = high-concurrency indexing/analysis & job orchestration.

## 4) Data model (key tables)

- `users, repos, repo_links`
- `files(path, lang, commit, hash)`
- `symbols(name, kind, range, refs_json)`
- `chunks(file_id, start, end, summary, embedding VECTOR)`
- `events(kind, payload_json)`
- `runs(run_id, type, input_json, status, metrics_json, artifact_uri)`
- `facts(scope, key, value_json, source, run_id)` ← “function cards,” “module dossiers,” etc.
- `risks(item, score, features_json)`
- `answers(question, answer, cited_ids[], policy_version)`
- `retrieval_logs(...)`, `feedback(...)`
- `policies(kind, params_json, score, version)` ← reranker & prompt policy

## 5) Indexing & retrieval (baseline “learning”)

**Indexer (Go)**

- Clone/update (shallow), compute **diff**.
- **Parse** with tree-sitter; **chunk** by symbol; **summarize** (Python micro-service).
- **Embed** (code + summary) → pgvector; update **symbol/call graph**.

**Chat (Python)**

- Hybrid retrieve: semantic (KNN) + symbolic/lexical + recency + history.
- Build context (chunks + summaries + graph hops), call LLM.
- Return **answer + citations (file:line + commit)**; log retrieval set.

## 6) Continual Learning (the “never-stop thinking” engine)

**Thought = atomic background job** with inputs, budget, outputs → persisted artifacts.

**Core Thought types:**

- `ScanDiff`, `MapRepo` (graph & coverage of codebase)
- `SmellHunt` (linters, security rules, complexity)
- `HypothesizeBug` (LLM proposes failure modes from diffs/smells/history)
- `GenTests` (unit/property tests), `Fuzz` (coverage-guided)
- `Profile` (micro-benchmarks on hot paths)
- `PatchDraft` (safe refactors/guards; user-review PR)
- `Verify` (run tests/benchmarks; attach logs)
- `Summarize` (function cards, change digests)
- `Prioritize` (update frontier via bandit/metrics)

**Scheduler (Go)**

- Priority queues per repo + global; **goroutine** worker pool with work-stealing.
- **Token-bucket budgets** per repo (CPU/GPU minutes, I/O); quiet hours/night mode.
- Triggers: **webhooks** (event-driven) + **cadence** (cron).
- Sandbox dynamic jobs in containers; cancellable contexts; exponential backoff.

**What “learning” means**

- **Knowledge growth (no weight changes):** embeddings, graphs, “facts” (cards/dossiers), artifacts from tests/fuzz/benchmarks—become durable, queryable context.
- **Behavioral adaptation (small models, frequent updates):**
  - **Retrieval Reranker** (logreg/XGBoost/cross-encoder): learns which chunks help; retrain daily.
  - **Prompt/Context Policy** (multi-armed bandit): picks #chunks, summaries, graph hops, temperature/system-prompt; per-repo best policy promoted.
  - **Scheduler bandit:** allocates Thought types to what pays off (e.g., more fuzzing for parsers).
- **Optional later:** **per-repo LoRA adapter** (after enough curated Q&A/patches); gated by held-out eval; tenant-scoped.

**Risk scoring (guides thinking)**

- Features: churn, centrality (call-graph PageRank), complexity, coverage gap, smells/security severity, recent diffs, (later) CI/incident signals.
- Drives `HypothesizeBug`, `GenTests`, `Profile` targets.

## 7) Frontend (Next.js + TS + Tailwind + shadcn/ui)

- **Repos**: connect via GitHub OAuth/App; index status; Continuous Learning **toggle**.
- **Repo view**:
  - **Chat** with sources panel (click → code viewer at cited lines).
  - **Learning status**: “Indexed 2m ago · 3 thoughts running · 12 queued · Policy v7.”
  - **Insights feed**: evidence-backed items (“Semgrep rule X flagged… [Repro] [Draft test]”).
  - **Risk heatmap**: tree/file; click → function card (facts, tests, owners).
  - **Runs tab**: each run’s logs, coverage, artifacts.
  - **Settings**: budgets, quiet hours, allowed tools, PR permissions.
  - **Why this answer?**: top retrieval features + policy version; full citations.

## 8) APIs (minimal contract)

- `POST /webhooks/github`
- `POST /index/{repo}/initial` / `POST /index/{repo}/diff`
- `POST /learning/toggle {repo_id, on, budgets}`
- `GET /learning/status?repo_id=...`
- `GET /insights?repo_id=&filter=...`
- `POST /chat {repo_id, question}` → `{answer, citations, policy_version}`
- `POST /feedback {answer_id, vote, note, correct_citations?}`
- `POST /runs/{run_id}/rerun`

## 9) Tooling

- **Static**: tree-sitter, Semgrep, ESLint/flake8/golangci-lint, mypy/tsc.
- **Tests**: pytest/jest/go test; **property tests** (Hypothesis/fast-check).
- **Fuzz**: Go fuzz/libFuzzer (where supported).
- **Perf/Profiling**: go bench/pprof, pytest-benchmark, Node prof (opt-in).
- **LLM/Embeddings**: provider-abstracted; start API, swap to self-host later.

## 10) Security & guardrails

- Tenant-scoped data; encrypt at rest; private VPC.
- No auto-commits; **PR drafts only** with explicit user action.
- Secret hygiene (never leak code to third-party tools); sandbox execution.
- Rate limits, kill-switch, rollbacks for policies/reranker.

## 11) Implementation roadmap (lean)

1. Auth + repo connect → **initial index** → **chat with citations**.
2. Webhooks → **diff index** (freshness).
3. Continual Learning ON → **MapRepo, SmellHunt, Prioritize**; insights feed + status.
4. **GenTests/Verify/Fuzz/Profile** + artifacts UI.
5. Nightly **reranker & policy** training; A/B gate; live “Why this?” UI.
6. PR draft flow; risk heatmap; function cards.
7. (Later) per-repo LoRA; CI/incident signals; multi-repo/org mode.

# 20‑Week Build Plan — Repo‑Aware Chat + Continual Learning Engine

**Target audience:** Solo dev or small team starting from scratch in VS Code  
**Stack (recommended):**

- **Frontend:** Next.js (React + TypeScript), Tailwind, shadcn/ui, Monaco editor
- **Brain (Python):** FastAPI, SQLAlchemy + Alembic, pgvector, LangChain (provider‑abstracted), tree‑sitter bindings (via service call)
- **Thinker (Go):** Go 1.22+, go-git, tree-sitter CLI, Semgrep, ESLint/flake8/golangci-lint runners, NATS/Redis client
- **Data:** Postgres 16 + pgvector, Redis or NATS (queue), MinIO (S3‑compatible artifacts)
- **Infra (local):** Docker + docker-compose, Makefile, .env files
- **Auth:** GitHub OAuth App (later GitHub App for PR drafts)

---

## Monorepo Layout (from day 1)

```text
repo-root/
├─ apps/
│  └─ web/                      # Next.js (TS)
├─ services/
│  ├─ brain-python/             # FastAPI + RAG + policies
│  └─ thinker-go/               # Go workers (indexing, analysis, scheduler)
├─ packages/
│  └─ shared/                   # Shared schemas, OpenAPI client, utils
├─ infra/
│  ├─ docker-compose.yml
│  ├─ migrations/               # Alembic migrations
│  ├─ seed/                     # Seed SQL & test repos
│  └─ k8s/                      # (later) manifests
├─ db/
│  └─ models.sql                # (generated by Alembic, docs only)
├─ docs/
│  ├─ brief.md                  # high-level brief (your existing file)
│  └─ build-plan-20w.md         # this file
├─ scripts/                     # dev scripts (bootstrap, lint, test, demo)
├─ .env.example
└─ Makefile
```

**.env.example (root)**

```env
# shared
POSTGRES_USER=dev
POSTGRES_PASSWORD=devpass
POSTGRES_DB=repochat
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0
NATS_URL=nats://nats:4222

S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_BUCKET=artifacts

# web
NEXTAUTH_SECRET=changeme
NEXTAUTH_URL=http://localhost:3000
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx

# brain
EMBEDDING_MODEL=bge-base-en
LLM_PROVIDER=openai
LLM_API_KEY=xxx

# thinker
GITHUB_WEBHOOK_SECRET=xxx
```

**Makefile (starter)**

```makefile
.PHONY: up down logs web brain thinker db mig seed fmt lint test

up:
\tdocker compose -f infra/docker-compose.yml up -d --build
down:
\tdocker compose -f infra/docker-compose.yml down -v
logs:
\tdocker compose -f infra/docker-compose.yml logs -f --tail=200

web:
\tdocker compose -f infra/docker-compose.yml exec web pnpm dev
brain:
\tdocker compose -f infra/docker-compose.yml exec brain uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
thinker:
\tdocker compose -f infra/docker-compose.yml exec thinker go run ./cmd/worker

db:
\tdocker compose -f infra/docker-compose.yml exec brain alembic upgrade head
mig:
\tdocker compose -f infra/docker-compose.yml exec brain alembic revision --autogenerate -m "$(m)"
seed:
\tdocker compose -f infra/docker-compose.yml exec brain python scripts/seed.py

fmt:
\tdocker compose -f infra/docker-compose.yml exec thinker go fmt ./...
\tdocker compose -f infra/docker-compose.yml exec brain ruff check --fix . || true
\tdocker compose -f infra/docker-compose.yml exec web pnpm format

lint:
\tdocker compose -f infra/docker-compose.yml exec thinker golangci-lint run || true
\tdocker compose -f infra/docker-compose.yml exec brain ruff check . || true
\tdocker compose -f infra/docker-compose.yml exec web pnpm lint

test:
\tdocker compose -f infra/docker-compose.yml exec brain pytest -q || true
```

**docker-compose (key services)**

```yaml
services:
  web:
    build: ./apps/web
    env_file: .env
    ports: ["3000:3000"]
    depends_on: [brain]
  brain:
    build: ./services/brain-python
    env_file: .env
    ports: ["8000:8000"]
    depends_on: [postgres, redis, minio]
  thinker:
    build: ./services/thinker-go
    env_file: .env
    depends_on: [brain, nats, postgres, minio]
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports: ["5432:5432"]
  redis:
    image: redis:7
    ports: ["6379:6379"]
  nats:
    image: nats:2
    ports: ["4222:4222"]
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${S3_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY}
    ports: ["9000:9000", "9001:9001"]
```

---

## Definition of Done (per feature)

- **Code runs locally** via `docker compose up` with `.env` filled.
- **Unit/integration tests** exist for new components.
- **Docs updated** (README, API docs, example requests).
- **Telemetry/logs** visible in container logs.
- **Security/permissions** minimal & explicit.

---

## 20‑Week Sprint Plan (from zero → full MVP)

### Week 1 — Dev Environment & Monorepo Bootstrap

**Goals**

- Initialize monorepo; set up `apps/web`, `services/brain-python`, `services/thinker-go` skeletons.
- Docker compose for Postgres, Redis/NATS, MinIO.
- Basic Makefile + `.env.example`.

**Tasks**

- Node/PNPM, Python (uv/poetry), Go modules; ESLint/Prettier, Ruff/Black, golangci-lint.
- Healthcheck endpoints: `/healthz` on web, brain, thinker.
- Commit CI stub (GitHub Actions) to lint/build containers.

**Acceptance**

- `docker compose up` shows web @3000, brain @8000 responding `/healthz`.
- CI green on lint/build.

---

### Week 2 — Database Schema & Migrations

**Goals**

- Postgres + pgvector installed.
- Alembic migrations for core tables (users, repos, files, chunks, embeddings, symbols, events, runs, facts, risks, answers, retrieval_logs, feedback, policies).

**Tasks**

- SQLAlchemy models; `alembic revision --autogenerate`; seed script for test data.
- Minimal DB client in Go (read-only) for Thinker where needed (or HTTP to Brain).

**Acceptance**

- `make db && make seed` succeeds; tables present; sample rows visible.

---

### Week 3 — Frontend Shell & Auth Scaffolding

**Goals**

- Next.js app with Tailwind + shadcn/ui; layout & routing.
- NextAuth GitHub OAuth (login/logout); session indicator.

**Tasks**

- Pages: `/`, `/login`, `/dashboard` (protected).
- Auth guard HOC; API proxy to Brain with auth header.

**Acceptance**

- Can sign in with GitHub, see dashboard skeleton.

---

### Week 4 — GitHub Connect (Repo Picker)

**Goals**

- UI to connect GitHub, list repos (read scope).
- Persist selected repo in DB (`repos`, `repo_links`).

**Tasks**

- Backend route: `POST /repos/connect`, `GET /repos/list` via GitHub REST.
- Store owner/name/default_branch; display index status.

**Acceptance**

- Pick 1 repo → stored; dashboard shows repo card “Not indexed”.

---

### Week 5 — Initial Indexer (Go) + Embeddings (Brain)

**Goals**

- Clone shallow repo; parse, chunk, summarize, embed; store chunks + symbols.
- Expose status in UI.

**Tasks**

- Thinker: `initial_index(repo@commit)` job; tree-sitter boundaries; filters.
- Brain: embed API; summaries (LLM) with budget guard.
- UI: progress + “Indexed at …”.

**Acceptance**

- Selecting repo triggers index; DB shows chunks/embeddings; UI marks Indexed.

---

### Week 6 — RAG Chat (Repo-Aware) with Citations

**Goals**

- Chat endpoint (Brain) that retrieves top‑K chunks + summaries; LLM answers with **file:line + commit** citations.
- Web chat UI + sources panel + code viewer.

**Tasks**

- Retrieval: semantic (KNN via pgvector) + lexical/symbol boost + recency.
- Return citations; UI opens file viewer at line.
- Log retrieval set in `retrieval_logs` and message in `answers`.

**Acceptance**

- Ask “Where is auth?” → answer with correct file:line; sources clickable.

---

### Week 7 — Webhooks & Diff Index (Freshness)

**Goals**

- GitHub webhooks (`push`, `pull_request`) → `diff_index` job to re-embed changed files only.
- Show “Last updated …” and queued jobs.

**Tasks**

- Thinker: diff vs base; re‑chunk; upsert embeddings/symbols.
- Brain: expose `/index/status`.
- UI: status bar (indexed at, running, queued).

**Acceptance**

- Push change to repo → within seconds/minutes, chunks update; chat reflects new code.

---

### Week 8 — Continual Learning Toggle + Scheduler Skeleton

**Goals**

- Toggle in UI to enable “Continual Learning.”
- Go scheduler (priority queues, budgets, cron).

**Tasks**

- Endpoints: `POST /learning/toggle`, `GET /learning/status`.
- Token-bucket budget, quiet hours; worker pool with work-stealing.

**Acceptance**

- Toggle ON shows active scheduler; queues visible; budgets enforceable.

---

### Week 9 — SmellHunt (Static Analysis) + Insights Feed

**Goals**

- Run ESLint/flake8/golangci-lint + Semgrep on repo; persist findings as `facts` + `insights`.
- UI “Insights” feed with filters & links to file:line.

**Tasks**

- Containerized runners; severity mapping; dedupe by hash.
- Feed UI with pagination; mark as read.

**Acceptance**

- Insights appear with evidence & links; no false spam (basic thresholds).

---

### Week 10 — Risk Scoring & Prioritizer

**Goals**

- Compute risk per function/file (churn, centrality, complexity, coverage gap, smells).
- Prioritizer Thought to pick next targets.

**Tasks**

- Build call graph from symbols/refs; PageRank; churn from git log.
- Persist `risks`; render risk heatmap (tree view).

**Acceptance**

- Heatmap highlights hot spots; scheduler pulls from top‑risk items.

---

### Week 11 — Test Generation + Verify Loop

**Goals**

- `GenTests` Thought creates unit/property tests; `Verify` runs tests; record coverage delta & logs.

**Tasks**

- Language‑specific skeletons (pytest/jest/go test).
- Property‑based tests (Hypothesis/fast‑check) for parsers/validators.
- UI: Runs tab with artifacts.

**Acceptance**

- New tests generated & executed; coverage delta recorded; artifacts downloadable.

---

### Week 12 — Fuzzing & Micro‑Benchmarks

**Goals**

- `Fuzz` Thought for supported langs; `Profile` micro-benchmarks on hot functions.

**Tasks**

- Go fuzz; libFuzzer harness where practical; pytest-benchmark; go bench; pprof snapshots.
- Store results; insights if regressions detected.

**Acceptance**

- Fuzzing finds failures on seeded functions; perf diffs visible across runs.

---

### Week 13 — Reranker v1 (Learning from Feedback/Clicks)

**Goals**

- Train small reranker (logreg/XGBoost) using `retrieval_logs` + feedback; hot‑reload in Brain.

**Tasks**

- Feature set: similarity, symbol/dir proximity, recency, past utility.
- Daily job; persistence in `policies`; A/B compare vs baseline.

**Acceptance**

- Offline AUC > baseline; online wins (click‑through or thumbs) over a day.

---

### Week 14 — Prompt/Context Policy Bandit

**Goals**

- Multi‑armed bandit to pick prompt/template (#chunks, summaries, graph hops, temp).

**Tasks**

- UCB/Thompson; reward proxy = user feedback + follow‑up rate.
- Persist current best policy per repo; expose in UI “Policy vX”.

**Acceptance**

- Bandit converges; measurable lift on acceptance metrics.

---

### Week 15 — PR Draft Flow (Safe Actions)

**Goals**

- `PatchDraft` Thought proposes small refactors/guards; user reviews diff; “Create PR” via GitHub App.

**Tasks**

- Draft branch naming; commit message template; limit diff size & scope.
- UI review modal; explicit permission gate.

**Acceptance**

- User reviews and creates PR; CI passes; no auto‑merge.

---

### Week 16 — “Why this Answer?” + Provenance UX

**Goals**

- UI panel showing retrieval features (recency, symbol match) + policy version; always show citations.

**Tasks**

- Brain returns provenance metadata; UI tooltips/chips; link to Runs/Insights when relevant.

**Acceptance**

- Users can trace every claim to evidence; trust improves (qualitative).

---

### Week 17 — Security Hardening & Tenant Isolation

**Goals**

- Encrypt at rest; strict scopes; sandbox dynamic runs; secret scanning; rate limits & kill switch.

**Tasks**

- Vault/KMS for secrets (local dev: dotenv); network egress off for jobs; per‑tenant S3 prefixes.
- Access checks on all APIs; audit log table.

**Acceptance**

- Threat checklist passes; manual pen‑test on endpoints; audit logs populate.

---

### Week 18 — Telemetry, Evals, and Nightly Jobs

**Goals**

- Centralized logs/metrics; nightly eval suite for retrieval & policy; dashboards.

**Tasks**

- Basic Prometheus/Grafana or OpenTelemetry to stdout + dev dashboard.
- Golden Q&A set per repo; eval harness; nightly reports in Insights.

**Acceptance**

- Dashboards show traffic, latency, job success; eval report generated nightly.

---

### Week 19 — Polish UX + Docs + Samples

**Goals**

- Empty‑state guides, tooltips, onboarding checklist; sample repos and demo script.
- API docs (OpenAPI) + quickstart docs.

**Tasks**

- Monaco code viewer polish; keyboard nav; toasts; loading states.
- `docs/` updates; screenshots/gifs.

**Acceptance**

- A new user can connect a repo and get value in < 5 minutes.

---

### Week 20 — Stabilization & Optional LoRA Pilot

**Goals**

- Bug bash; performance passes; optional per‑repo LoRA adapter trial (if enough curated data).

**Tasks**

- Load test chat & indexer; optimize context building; cold‑start improvements.
- LoRA: prepare curated triples; gated eval; tenant‑scoped artifacts.

**Acceptance**

- MVP stable under dev load; LoRA (if attempted) passes held‑out eval without regressions.

---

## Command Quickstart (local)

```bash
# 0) Copy .env.example to .env and fill secrets
cp .env.example .env

# 1) Bring everything up
make up && make db && make seed

# 2) Dev servers
make logs        # watch logs
# In terminals as needed:
make web         # Next.js dev
make brain       # FastAPI reload
make thinker     # Go worker

# 3) First run
# - Login on http://localhost:3000
# - Connect a repo
# - Trigger "Initial Index"
# - Ask a question in chat and see citations
# - Toggle Continual Learning and watch Insights
```

## Testing Strategy

- **Unit tests:** retrieval, ranker features, parsers, risk scoring.
- **Integration:** end‑to‑end index → chat with citations; webhook diff → updated answer.
- **Regression:** nightly eval against golden Q&A; track win rate.
- **Security:** route guards, scope tests, sandbox leak tests.
- **Performance:** latency budgets for chat (<2s P95 locally), indexer throughput.

## Risks & Mitigations

- **Over‑eager background compute** → strict budgets/quiet hours + kill switch.
- **Hallucinated insights** → require artifacts (repro/logs/tests) for claims.
- **Data privacy** → tenant isolation, encryption, no third‑party code exfil.
- **Vendor lock‑in** → provider‑abstracted LLM/embeddings; Dockerized services.
- **Complexity creep** → 20‑week scope discipline; ship value by Week 6–8.

---
