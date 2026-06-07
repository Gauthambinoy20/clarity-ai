# Contributing to ClarityAI

Thank you for your interest in contributing to ClarityAI. This guide covers everything you need to get the project running locally, the code standards we enforce, and how to submit a pull request.

---

## Table of Contents

1. [Backend Setup](#backend-setup)
2. [Frontend Setup](#frontend-setup)
3. [Code Standards](#code-standards)
4. [Testing](#testing)
5. [PR Process](#pr-process)

---

## Backend Setup

### Prerequisites

- Python 3.12+
- `git`

### Steps

```bash
# 1. Clone the repo (if you haven't already)
git clone https://github.com/your-username/ClarityAI.git
cd ClarityAI/backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

# 3. Install runtime dependencies
pip install -r requirements.txt

# 4. Install dev dependencies (linters, test runners)
pip install -r requirements-dev.txt

# 5. Download the spaCy language model
python -m spacy download en_core_web_sm

# 6. Download NLTK data packages
python -c "
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
"

# 7. Start the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/api/v1/docs`

### Environment Variables

Copy `.env.example` to `.env` (or create `.env`) and adjust as needed.
Key variables:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./clarityai.db` | Database connection string |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama local LLM endpoint |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `DEBUG` | `False` | Enable FastAPI debug mode |

---

## Frontend Setup

### Prerequisites

- Node.js 18+
- npm 9+

### Steps

```bash
cd ClarityAI/frontend

# Install all dependencies (including dev)
npm install

# Start the Vite dev server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

Make sure the backend is also running so API calls resolve correctly.

---

## Code Standards

We enforce consistent style across the codebase using automated tooling.

### Backend (Python)

| Tool | Purpose | Config |
|---|---|---|
| **black** | Auto-formatter | `pyproject.toml` |
| **ruff** | Linter (flake8-compatible) | `pyproject.toml` |
| **mypy** | Static type checker | `pyproject.toml` |

Run all checks:

```bash
cd backend

# Format code
black app/ tests/

# Lint
ruff check app/ tests/

# Type-check
mypy app/
```

Key settings: line length 100, target Python 3.12, `select = ["E", "F", "W", "I"]`.

### Frontend (TypeScript / React)

| Tool | Purpose | Config |
|---|---|---|
| **ESLint** | Linter | `.eslintrc.json` |
| **Prettier** | Formatter | `.prettierrc` |

Run all checks:

```bash
cd frontend

# Lint
npm run lint

# Auto-format source files
npm run format
```

Key settings: 100 character print width, double quotes, trailing commas (ES5 style).

### General Rules

- No committed `.pyc` files or `__pycache__` directories (covered by `.gitignore`).
- No committed `node_modules/`.
- No committed `.env` files containing secrets.
- All new Python modules must include a module-level docstring.
- All new React components must be typed with TypeScript interfaces (no `any` without justification).

---

## Testing

### Backend Tests

Tests live in `backend/tests/` and are run with `pytest`.

```bash
cd backend

# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_api.py -v

# Run a specific test
pytest tests/test_detectors.py::TestEntropyAnalyzerDetector -v
```

The `pytest.ini` file sets `asyncio_mode = auto`, so async tests work without extra decorators beyond `@pytest.mark.asyncio`.

CI requires at least 50% coverage (`--cov-fail-under=50`).

### Frontend Tests

Tests live in `frontend/src/__tests__/` and are run with Vitest.

```bash
cd frontend

# Run all tests once
npm run test

# Run with coverage
npm run test:coverage
```

---

## PR Process

1. **Fork** the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** following the code standards above.

3. **Add tests** for any new logic. Backend changes should include pytest tests; new React components should include Vitest tests.

4. **Run the full test suite** and ensure everything passes before opening a PR.

5. **Push** your branch and open a Pull Request against `main`.

6. **PR checklist**:
   - [ ] Tests pass locally (`pytest` and `npm run test`)
   - [ ] Linting passes (`ruff check app/` and `npm run lint`)
   - [ ] No new `any` types in TypeScript without justification
   - [ ] Description explains *why* the change is needed, not just *what* changed
   - [ ] Linked to a GitHub issue if one exists

7. A maintainer will review your PR. Please respond to feedback within a reasonable time. PRs with no activity for 14 days may be closed.

---

For questions, open a GitHub Discussion or file an issue.
