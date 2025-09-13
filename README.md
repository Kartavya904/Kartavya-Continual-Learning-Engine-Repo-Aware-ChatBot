# Repo-Aware Chat + Continual Learning Engine

> Connect a GitHub repo → get a repo-aware chat with file:line citations, diff-freshness, and an always-on “thinking” engine that maps risks, drafts tests/PRs, and proves claims with artifacts.

![status](https://img.shields.io/badge/status-MVP_plan-blue)
![stack](https://img.shields.io/badge/stack-Next.js%20%7C%20FastAPI%20%7C%20Go%20%7C%20Postgres%20%2B%20pgvector-informational)

> **License:** All Rights Reserved — viewing only. No use/modification/distribution without written permission.

---

## Why this exists

Most code assistants answer confidently but can’t show receipts or keep up with a moving codebase. This project ships a repo-aware chat that:

- **Cites sources** at file:line with commit pins.
- **Stays fresh** by indexing diffs on pushes/PRs.
- **Thinks in the background** (opt-in): static/dynamic checks, risk mapping, test generation, fuzzing, profiling, and safe PR drafts—feeding findings back into chat and the UI.

---

## Core features

- **Repo-aware chat** with hybrid retrieval (semantic + symbolic + recency) and file:line citations.
- **Diff indexing** via webhooks; only changed files are re-embedded.
- **Continual Learning** (toggle): composable “Thoughts” like `ScanDiff`, `SmellHunt`, `GenTests`, `Fuzz`, `Profile`, `PatchDraft`, `Verify`, `Summarize`, `Prioritize`.
- **Provenance UI**: “Why this answer?” panel shows retrieval features + policy version; every claim links to evidence.
- **Insights feed**: evidence-backed items with repro logs/tests.
- **Risk heatmap**: per file/function using churn, graph centrality, complexity, coverage gaps, smell/security severity, etc.
- **Safe actions**: PRs are **draft-only** and never auto-merge.

---

## Architecture (Python + Go microservices)

```text
[Next.js/React/TS] ─► [API Gateway]
      │
      ├─► Python “Brain” (FastAPI)
      │     • Chat (LLM + RAG + citations)
      │     • Reranker & prompt policy (bandit)
      │     • Summarizers, test synthesis
      │
      ├─► Go “Thinker” Workers
      │     • Webhooks, scheduler (priority + budgets)
      │     • Clone/diff, parse (tree-sitter), embed
      │     • Static/dynamic checks, fuzz, bench
      │     • PR draft (never auto-merge)
      │
      └─► Stores
            • Postgres 16 (+ pgvector)
            • Object storage (artifacts)
            • Queue (Redis/NATS)
```

**Split of concerns:** Python for LLM/RAG + small models; Go for high-concurrency indexing/analysis & job orchestration.

---

## Monorepo layout

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
│  └─ k8s/                      # (later)
├─ db/
│  └─ models.sql                # (generated docs)
├─ docs/
│  ├─ brief.md                  # high-level brief
│  └─ build-plan-20w.md         # detailed plan
├─ scripts/                     # bootstrap, lint, test, demo
├─ .env.example
└─ Makefile
```

---

## Quickstart (local dev)

**Prereqs:** Docker, docker-compose, Make, Git.

```bash
# 0) Copy env and fill secrets (see Config)
cp .env.example .env

# 1) Bring up the stack
make up && make db && make seed

# 2) Dev servers (run in separate terminals as needed)
make logs        # tail all containers
make web         # Next.js dev on :3000
make brain       # FastAPI reload on :8000
make thinker     # Go worker

# 3) First run in the browser
# - http://localhost:3000 → Login (GitHub OAuth)
# - Connect a repo
# - Trigger "Initial Index"
# - Ask a question; click citations to open code at line
# - Toggle Continual Learning; watch Insights populate
```

---

## Configuration

Set via `.env` (copy from `.env.example`):

| Section        | Key                                                                 | Example                  | Notes                      |
| -------------- | ------------------------------------------------------------------- | ------------------------ | -------------------------- |
| Postgres       | `POSTGRES_*`                                                        | `repochat@postgres:5432` | pgvector enabled           |
| Queue          | `REDIS_URL` / `NATS_URL`                                            | `redis://redis:6379/0`   | choose one or both         |
| Artifacts (S3) | `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`        | `http://minio:9000`      | stores logs, repro bundles |
| Web (NextAuth) | `NEXTAUTH_SECRET`, `NEXTAUTH_URL`                                   | `http://localhost:3000`  | GitHub OAuth required      |
| GitHub         | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_WEBHOOK_SECRET` | `xxx`                    | App/ OAuth setup           |
| LLM            | `LLM_PROVIDER`, `LLM_API_KEY`, `EMBEDDING_MODEL`                    | `openai`, `bge-base-en`  | provider-abstracted        |

---

## Make targets (high-signal)

```makefile
up / down / logs
db          # alembic upgrade head
mig m="..." # autogenerate migrations
seed        # seed demo data
fmt         # format Go/Python/TS
lint        # run linters across services
test        # run Python tests (expand per service)
```

---

## Data model (key tables)

`users`, `repos`, `repo_links`, `files`, `symbols`, `chunks (VECTOR)`, `events`, `runs`, `facts`, `risks`, `answers`, `retrieval_logs`, `feedback`, `policies`.

---

## Retrieval & chat

- **Indexer (Go):** shallow clone; diff; parse (tree-sitter); chunk by symbol; summarize; embed (code + summary) → pgvector; update symbol/call graph.
- **Chat (Python):** hybrid retrieve (KNN + symbol/lexical + recency + history); build context; answer with **file:line + commit** citations.

---

## Continual Learning (opt-in)

**Thoughts** are atomic background jobs with inputs, budgets, outputs → persisted artifacts.

- Discovery: `ScanDiff`, `MapRepo`
- Quality & safety: `SmellHunt`, `HypothesizeBug`
- Tests & robustness: `GenTests`, `Fuzz`, `Verify`
- Performance: `Profile`
- Action: `PatchDraft` (PR draft, no auto-merge)
- Knowledge: `Summarize` (function cards), `Prioritize` (bandit)

**Scheduler (Go):** priority queues per repo, goroutine pool with work-stealing, **token-bucket budgets** (CPU/GPU/I/O), quiet hours, webhook + cron triggers, container sandboxing, backoff.

**Learning loops (no big model fine-tune required):**

- **Retrieval Reranker:** learns which chunks help; retrains on logs/feedback.
- **Prompt/Context Policy bandit:** picks #chunks, summaries, graph hops, temperature/system prompt per repo.
- **Scheduler bandit:** allocates Thought types by payoff.
- (Later) **per-repo LoRA** after enough curated triples (gated by held-out eval).

---

## HTTP API (minimum contract)

```
POST /webhooks/github
POST /index/{repo}/initial
POST /index/{repo}/diff
POST /learning/toggle           # {repo_id, on, budgets}
GET  /learning/status
GET  /insights?repo_id=&filter=
POST /chat                      # -> {answer, citations, policy_version}
POST /feedback
POST /runs/{run_id}/rerun
```

---

## Frontend UX

- **Dashboard:** connect repo(s), index status, CL toggle.
- **Repo view:** Chat + sources panel (open code at cited lines), Insights feed, Risk heatmap (tree/file), Runs tab (logs, coverage, artifacts), Settings (budgets, quiet hours, PR perms), **Why this answer?** panel.

---

## Security & guardrails

- Tenant-scoped data; encryption at rest.
- No auto-commits; **PR drafts only** and explicit user permission.
- Secret hygiene (no third-party code exfil).
- Rate limits, kill-switch; job sandboxing; audit logs.

---

## Testing & quality

- **Unit:** retrieval features, parsers, risk scoring.
- **Integration:** end-to-end index → chat with citations; webhook diff → updated answers.
- **Regression:** nightly eval against golden Q&A; track win rate.
- **Performance:** chat latency budget (e.g., <2s P95 locally), indexer throughput.

---

## Roadmap (MVP path)

1. Auth + repo connect → **initial index** → **chat with citations**
2. Webhooks → **diff index** (freshness)
3. **Continual Learning** (MapRepo, SmellHunt, Prioritize) + Insights
4. **GenTests/Verify/Fuzz/Profile** with artifacts
5. Nightly **reranker & policy** training; **Why this?** UI
6. PR draft flow; Risk heatmap; Function cards
7. (Later) per-repo LoRA; CI/incident signals; multi-repo/org

A detailed, week-by-week plan lives in `docs/build-plan-20w.md`.

---

## Contributing

- Open a discussion for feature proposals; small PRs > big PRs.
- Keep diffs scoped; include tests and docs.
- Follow conventional commits (`feat:`, `fix:`, `docs:` …).
- Run `make fmt lint test` before pushing.

---

Copyright (c) 2025 Kartavya Singh. All rights reserved.

This repository is provided for viewing and learning purposes only.
No permission is granted to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the software, in whole or in part,
without prior written permission from the copyright holder.
