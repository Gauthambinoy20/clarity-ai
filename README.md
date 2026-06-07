# ClarityAI — AI Content Analysis Portfolio Project

[![CI](https://github.com/gauthambinoy/cipher-prose-truth/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)

ClarityAI is a full-stack AI text analysis app built to demonstrate production-oriented NLP engineering: a FastAPI backend, React/TypeScript frontend, Dockerized local development, CI, and free-tier deployment paths.

**Live demo:** https://clarityai-pied.vercel.app
**API docs:** https://gxm00009-clarityai.hf.space/api/v1/docs

> Recruiter note: this is a portfolio project, not a claim of definitive authorship attribution. AI detection is probabilistic and should be used as a writing-signal assistant, not as evidence of misconduct.

---

## What it demonstrates

- **AI text detection:** ensemble scoring from language-model, stylometric, repetition, entropy, watermark, and pattern signals.
- **Text analytics:** readability, tone, grammar, SEO, citations, paraphrase, comparison, and statistics endpoints.
- **Humanization workflow:** rule-based and Ollama-assisted rewriting path for local experimentation.
- **Product UX:** dashboard, batch analysis, history, export/share surfaces, dark/light theme, and responsive navigation.
- **Production basics:** Dockerfiles, docker-compose, env examples, CORS config, health checks, CI, and Vercel/Render/Hugging Face deployment notes.

---

## Demo tour

| Area | What to show in a walkthrough |
|---|---|
| Detection dashboard | Paste a 100+ word passage, run analysis, explain overall score, signal breakdown, sentence heatmap, and GLTR visualization. |
| Analytics suite | Run readability/tone/statistics to show typed API responses and multi-tab product design. |
| Batch page | Add multiple text samples and discuss queue-oriented processing design. |
| API docs | Open `/api/v1/docs` to show FastAPI schemas and endpoint coverage. |

### Screenshots / GIFs

Recommended assets to add before pinning the repo:

1. `docs/screenshots/detection-dashboard.png`
2. `docs/screenshots/analytics-suite.png`
3. `docs/screenshots/api-docs.png`
4. `docs/screenshots/demo-walkthrough.gif` (30-60 seconds)

The deployed app is live, so screenshots can be captured from the Vercel URL without changing code.

---

## Architecture

```text
Browser
  |
  | React 18 + TypeScript + Vite + MUI
  v
Vercel static frontend
  |
  | /api/v1/*
  v
FastAPI backend (Docker on Hugging Face Spaces or Render)
  |
  |-- SQLite + SQLAlchemy async models
  |-- spaCy / NLTK / scikit-learn / transformers
  |-- Optional Ollama endpoint for local LLM rewriting
```

Key files:

```text
backend/app/main.py              FastAPI app factory, CORS, lifespan, routers
backend/app/api/routes/          REST/WebSocket endpoints
backend/app/ml/detectors/        Detection signal implementations
backend/app/ml/analyzers/        Readability, tone, SEO, stats, citations, etc.
frontend/src/pages/              Main product screens
frontend/src/components/         Reusable UI by feature area
docker-compose.yml               Local full-stack run
.github/workflows/ci.yml         Backend/frontend/Docker validation
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for deeper implementation notes.

---

## Accuracy and limitations

AI text detection is an active research problem. This project intentionally exposes caveats:

- Scores are **probabilities/signals**, not proof.
- Short text, heavily edited text, non-native writing, templates, and domain jargon can produce false positives or false negatives.
- Claimed accuracy depends on benchmark composition; production users should validate on their own corpus.
- The free hosted backend can cold-start and may be slower on transformer-heavy endpoints.
- Ollama humanization is optional and intended for local experimentation; it is not required for the live demo.

Recommended use: writing feedback, editorial triage, and model-behavior exploration.

---

## Sample report

A compact example response is available at [`docs/sample-detection-report.json`](docs/sample-detection-report.json).

```json
{
  "overall_score": 0.73,
  "classification": "mixed",
  "confidence": "medium",
  "top_signals": ["gltr", "repetition", "entropy_analyzer"],
  "recommended_action": "Review highlighted sentences instead of treating the result as final proof."
}
```

---

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 20+ and npm
- Docker Desktop or Docker Engine (optional but recommended)
- Ollama (optional, only for local LLM humanization)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger'); nltk.download('stopwords')"
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: http://localhost:8000/api/v1/docs

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

Frontend: http://localhost:5173

### Docker Compose

```bash
SECRET_KEY="dev-only-change-me" docker compose up --build
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000/api/v1/health

---

## Tests and quality gates

```bash
# Backend
cd backend
ruff check app/ --select E,F,W --ignore E501
black --check app/ tests/
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=20

# Frontend
cd frontend
npm run test
npm run build
```

CI runs the same backend tests, frontend tests/build, and a backend Docker image smoke test. The current coverage gate is intentionally modest for a broad portfolio app; raising it to 50%+ is a good next hardening milestone.

---

## Free deployment guide

### Frontend on Vercel

1. Import the GitHub repo in Vercel.
2. Set project root to the repository root.
3. Use:
   - Build command: `cd frontend && npm ci && npm run build`
   - Output directory: `frontend/dist`
4. Keep `vercel.json` rewrites if using the Hugging Face backend, or set `VITE_API_URL=https://your-backend.example.com/api/v1`.
5. Deploy and verify `/`, `/analytics`, and `/dashboard` routes refresh correctly.

### Backend on Hugging Face Spaces (free Docker)

1. Create a new Space with **Docker** SDK.
2. Add the backend files or connect this repo with a Docker build that uses `backend/Dockerfile`.
3. Set environment variables:
   - `SECRET_KEY` = generated random string
   - `CORS_ORIGINS` = `https://your-vercel-app.vercel.app,http://localhost:5173`
   - `DATABASE_URL` = `sqlite+aiosqlite:///./clarityai.db`
4. Confirm `https://your-space.hf.space/api/v1/health` returns `200`.

### Backend on Render (free web service)

1. Connect the repo in Render.
2. Use the included `render.yaml` or configure Docker manually.
3. Set `SECRET_KEY` and `CORS_ORIGINS`.
4. Health check path: `/api/v1/health`.

Do not commit real secrets. Use provider environment-variable settings.

---

## Repository hygiene

Generated files are ignored (`__pycache__`, SQLite WAL files, build output, `node_modules`, `*.tsbuildinfo`, `.env`). Keep screenshots and sample reports under `docs/` so recruiters can review the product quickly.

## License

MIT. See [LICENSE](LICENSE).
