# ClarityAI Architecture

This document describes the internal architecture of ClarityAI — how the ML detection pipeline works, how the backend is structured, how the frontend is organised, the database schema, and how the application can be deployed on free tiers.

ClarityAI reports probabilistic writing signals. It is designed for portfolio demonstration, editorial triage, and NLP experimentation, not definitive authorship attribution.

---

## Table of Contents

1. [Overview](#overview)
2. [ML Detection Pipeline](#ml-detection-pipeline)
3. [FastAPI Backend Structure](#fastapi-backend-structure)
4. [Frontend React Architecture](#frontend-react-architecture)
5. [Database Design](#database-design)
6. [Deployment Architecture](#deployment-architecture)

---

## Overview

ClarityAI is a full-stack monorepo composed of:

- **`backend/`** — Python 3.12 + FastAPI application hosting 41 REST/WebSocket endpoints and all ML logic.
- **`frontend/`** — React 18 + TypeScript + Vite SPA with MUI v6 UI.
- **`docker-compose.yml`** — Orchestrates both services for local development.

```
ClarityAI/
├── backend/
│   ├── app/
│   │   ├── main.py          # App factory + lifespan hook
│   │   ├── core/            # Config (pydantic-settings), rate limiter, WebSocket manager
│   │   ├── db/              # SQLAlchemy ORM, async engine, table models
│   │   ├── api/routes/      # 10 router modules covering 41 endpoints
│   │   └── ml/
│   │       ├── detectors/   # 17 individual signal detectors
│   │       ├── ensemble/    # Stacked meta-learner (weighted average + optional sklearn model)
│   │       ├── humanizer/   # 3-layer adversarial humanization pipeline
│   │       ├── plagiarism/  # Winnowing + semantic match + source discovery
│   │       └── analyzers/   # 12 analytics modules (readability, tone, grammar, SEO, etc.)
│   ├── tests/               # pytest test suite
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── pages/           # 8 top-level page components
│   │   ├── components/      # 37 reusable components organised by feature
│   │   ├── hooks/           # 6 custom React hooks
│   │   ├── stores/          # Zustand global state
│   │   ├── types/           # TypeScript interfaces for analysis + analytics
│   │   ├── utils/api.ts     # Axios instance + all API call functions
│   │   └── theme/           # MUI theme config (dark + light)
│   └── package.json
│
├── .github/workflows/       # CI (ci.yml) and deploy (deploy.yml)
└── docker-compose.yml
```

---

## ML Detection Pipeline

### Signal Architecture

The detection system is built around 17 independent signals, each implemented as a subclass of `BaseDetector` in `backend/app/ml/detectors/`. Every detector implements a single async method:

```python
async def analyze(self, text: str) -> dict:
    # Must return: signal, ai_probability (0-1), confidence, details
```

The 17 signals fall into four categories:

| Category | Detectors |
|---|---|
| **Language model statistics** | Perplexity + Burstiness, Fast-DetectGPT, Binoculars, Ghostbuster, GLTR |
| **Zero-shot classifiers** | Zero-Shot Ensemble (3 RoBERTa models), Watermark Detection |
| **Linguistic / stylometric** | Stylometrics, Entropy Analyzer, Vocabulary Richness, POS Patterns, Repetition, Coherence |
| **Pattern matching** | AI Fingerprint, AI Pattern Database, Cross-Reference, Rewrite Detector |

### Ensemble Meta-Learner

`backend/app/ml/ensemble/meta_learner.py` combines all signals into a single score via a weighted-average stacking approach:

1. Each detector returns an `ai_probability` (0.0–1.0).
2. The meta-learner builds a feature vector using `DEFAULT_WEIGHTS` (per-signal weights tuned against a validation set).
3. Interaction features are computed for three high-signal pairs: (detectgpt, binoculars), (stylometric, entropy), (perplexity, burstiness).
4. If a trained sklearn model exists on disk it is used as a stacking estimator; otherwise the weighted average is returned directly.
5. Classification thresholds: `>= 0.85` → AI Generated; `0.50–0.85` → Likely AI / Mixed; `< 0.50` → Human Written. These are product thresholds, not proof thresholds; teams should recalibrate against their own validation corpus.

### Model Registry

`backend/app/ml/models/model_registry.py` is a singleton that lazy-loads and caches HuggingFace models (GPT-2 variants, RoBERTa classifiers, sentence-transformers) and the spaCy pipeline. Models are loaded on first use and unloaded on application shutdown.

### Humanization Pipeline

`backend/app/ml/humanizer/pipeline.py` runs an adversarial feedback loop:

1. **Layer 1 — Lexical** (`lexical_humanizer.py`): Replaces AI buzzwords, expands contractions, removes AI phrase patterns.
2. **Layer 2 — Structural** (`structural_humanizer.py`): Varies sentence length, inserts hedging language, adds fragments.
3. **Layer 3 — Ollama LLM** (`ollama_humanizer.py`): Sends text to a local Mistral-7B instance with a humanization prompt.
4. **Adversarial loop**: After each pass the text is re-scored. If the AI score is still above the target threshold (default 0.10) the pipeline repeats layers 2–3 with increasing temperature (up to 5 iterations).
5. **Post-check**: Meaning preservation is measured via cosine similarity of sentence embeddings.

---

## FastAPI Backend Structure

### Application Factory

`app/main.py` exposes a `create_app()` factory following the application factory pattern. The `lifespan` context manager handles:
- Database table creation (`init_db()`)
- NLTK data download
- Upload directory creation
- Model registry teardown on shutdown

### Router Layout

All routers are mounted under `/api/v1`:

| Module | Prefix | Key Endpoints |
|---|---|---|
| `health.py` | `/api/v1` | `GET /health`, `GET /history` |
| `detection.py` | `/api/v1` | `POST /detect`, `POST /detect/fast`, `POST /detect/batch` |
| `plagiarism.py` | `/api/v1` | `POST /plagiarism` |
| `humanization.py` | `/api/v1` | `POST /humanize`, `GET /models` |
| `analytics.py` | `/api/v1/analytics` | 10 analytics sub-endpoints |
| `advanced.py` | `/api/v1/advanced` | Fingerprint, version tracking, batch, coach |
| `dashboard.py` | `/api/v1/dashboard` | Stats, trends, top signals |
| `export.py` | `/api/v1/export` | PDF, JSON, CSV, share link |
| `realtime.py` | `/ws` | `WS /ws/detect` (WebSocket) |

### Rate Limiting

Implemented in `app/core/rate_limiter.py`. Default: 20 requests per IP per hour with a burst allowance of 5.

### Configuration

All settings live in `app/core/config.py` as a pydantic-settings `Settings` class. Values are read from environment variables or `.env` file, with sensible defaults for local development.

---

## Frontend React Architecture

### Routing

React Router v7 handles navigation across 8 pages:

| Page | Route | Description |
|---|---|---|
| `DetectPage` | `/` | Main AI detection interface |
| `PlagiarismPage` | `/plagiarism` | Plagiarism checker |
| `HumanizePage` | `/humanize` | Humanization studio |
| `AnalyticsPage` | `/analytics` | 9-tab analytics suite |
| `DashboardPage` | `/dashboard` | Usage stats and trends |
| `BatchPage` | `/batch` | Multi-file batch processor |
| `ComparePage` | `/compare` | Side-by-side text comparison |
| `HistoryPage` | `/history` | Analysis history with pagination |

### State Management

**Zustand** (`src/stores/appStore.ts`) manages global UI state:
- Theme mode (dark / light, persisted to `localStorage`)
- Current detection / plagiarism / humanization results
- Loading flag (`isAnalyzing`)
- Drawer open state
- Notification queue

**TanStack Query** manages server state for data fetching (caching, background refetching, loading/error states).

### Component Organisation

```
src/components/
├── analysis/        # SentenceHeatmap, SignalBreakdown, GLTRVisualization, SignalRadar
├── analytics/       # ReadabilityPanel, ToneAnalyzer, GrammarChecker, SEOAnalyzer, etc.
├── advanced/        # BatchProcessor, LiveTypingDetector, RewriteDetector, VersionHistory
├── common/          # ScoreGauge, LoadingProgress, ExportMenu, NotificationCenter
├── dashboard/       # DashboardPage (stats overview)
├── humanizer/       # HumanizerPanel
├── input/           # TextInput, FileUpload
└── plagiarism/      # PlagiarismReport
```

### API Layer

All backend communication goes through `src/utils/api.ts`, which exports a configured Axios instance plus individual typed async functions for every endpoint. The error interceptor normalises error messages from FastAPI's `detail` field.

### Theming

MUI v6 theme is defined in `src/theme/theme.ts` and supports full dark/light mode switching. The active theme mode is toggled via `useAppStore` and applied at the root `App.tsx` level via `ThemeProvider`.

---

## Database Design

ClarityAI uses **SQLite** with `aiosqlite` for async access. The schema is managed by SQLAlchemy ORM (no migrations — tables are created on startup via `Base.metadata.create_all`).

### Tables

#### `analyses`

Stores every AI-detection run.

| Column | Type | Description |
|---|---|---|
| `id` | `VARCHAR(32)` PK | UUID hex string |
| `input_text` | `TEXT` | Raw input text |
| `word_count` | `INTEGER` | Number of words |
| `overall_ai_score` | `FLOAT` | Ensemble score (0–1) |
| `classification` | `VARCHAR(32)` | `ai_generated`, `human_written`, `mixed` |
| `confidence` | `FLOAT` | Meta-learner confidence |
| `signals_json` | `TEXT` | JSON array of per-signal results |
| `sentence_scores_json` | `TEXT` | JSON array of sentence-level scores |
| `gltr_data_json` | `TEXT` | GLTR token probability data |
| `attribution_model` | `VARCHAR(128)` | Best-guess generating model |
| `processing_time_ms` | `INTEGER` | End-to-end latency |
| `model_version` | `VARCHAR(64)` | App version at time of analysis |
| `created_at` | `DATETIME` | UTC timestamp |

#### `plagiarism_results`

One row per matched source, linked to `analyses`.

| Column | Type | Description |
|---|---|---|
| `id` | `VARCHAR(32)` PK | UUID hex |
| `analysis_id` | FK → `analyses.id` | Parent analysis |
| `source_url` | `TEXT` | Matched source URL |
| `source_title` | `VARCHAR(512)` | Page title |
| `matched_text` | `TEXT` | The overlapping passage |
| `similarity_score` | `FLOAT` | Semantic similarity (0–1) |
| `method` | `VARCHAR(64)` | `semantic`, `exact`, `fuzzy` |

#### `humanization_results`

Stores humanization rewrites linked to analyses.

#### `batch_jobs`

Tracks multi-file batch processing jobs with status (`pending`, `processing`, `completed`, `failed`), file counts, and JSON results.

#### `analytics_results`

Stores analytics analysis results (readability, tone, grammar, etc.) independently from detection analyses.

#### `api_usage`

Per-request log for rate limiting and usage analytics. Stores client IP, endpoint, method, status code, and response time.

### SQLite Optimisations

On every new connection, three PRAGMAs are applied:
- `PRAGMA journal_mode=WAL` — Write-Ahead Logging for concurrent reads
- `PRAGMA foreign_keys=ON` — Enforce referential integrity
- `PRAGMA synchronous=NORMAL` — Balance durability vs. write speed

---

## Deployment Architecture

### Local Development

```
Browser (localhost:5173)
        |
   Vite Dev Server  ──────────→  FastAPI (localhost:8000)
        |                               |
  React hot-reload             SQLite + ML models
                                        |
                            Ollama (localhost:11434)  [optional]
```

### Production (Current Target)

```
User Browser
     |
  Vercel CDN  (frontend — React SPA, static build)
     |
  API requests  →  HuggingFace Spaces / Render  (backend — Docker)
                          |
                    Persistent SQLite volume
```

#### Frontend — Vercel

The Vite build output (`frontend/dist/`) is deployed to Vercel as a static site. `vercel.json` rewrites all routes to `index.html` for SPA routing and proxies `/api/*` to the hosted backend. Alternatively, set `VITE_API_URL` to a backend API root such as `https://your-backend.example.com/api/v1`.

#### Backend — HuggingFace Spaces or Render

The `backend/Dockerfile` builds a self-contained image with Python, all pip dependencies, spaCy model, NLTK data, and `curl` for container health checks. The container exposes port 8000. CORS origins are configured via `CORS_ORIGINS` to allow the Vercel frontend domain.

#### Docker Compose (self-hosted)

`docker-compose.yml` at the repo root orchestrates both services. The backend mounts a named volume for the SQLite database so data persists across container restarts.

### CI/CD

`.github/workflows/ci.yml` runs on every push/PR to `main`:

1. **Backend**: installs dependencies, runs `ruff` lint, runs `black --check`, then `pytest tests/ --cov=app --cov-fail-under=20`
2. **Frontend**: installs with `npm ci`, runs `vitest`, then `vite build`
3. **Docker**: builds the backend image and smoke-tests the `/api/v1/health` endpoint

`.github/workflows/deploy.yml` triggers on push to `main` and deploys frontend to Vercel and backend to Render when the relevant secrets are configured. Without secrets, it safely skips deployment.
