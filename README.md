### README.md – QUANTIQUAN AI Engine

```markdown
# 🧠 QUANTIQUAN AI Engine

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009485.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**QUANTIQUAN AI Engine** is a production‑ready, AI‑powered Security Decision Intelligence platform.  
It transforms raw security findings into **prioritised, explainable risk decisions** with business‑contextualised AI summaries.

> **AI explains, it never scores.**  
> Risk scoring is deterministic, auditable, and always transparent.

---

## 🚀 Key Features

- 🔢 **Deterministic Risk Scoring** – CVSS + business context + threat intelligence + asset criticality → Business Impact Score (BIS)
- 🧠 **AI‑Generated Business Summaries** – Non‑blocking, explainable narratives (Groq/OpenAI/Gemini/Ollama)
- 📊 **Confidence Scoring** – Data completeness and reliability metrics
- 📌 **Recommendation Engine** – Knowledge‑base driven remediation guidance
- 🔒 **Multi‑tenant Isolation** – Row‑level security in PostgreSQL
- 📡 **Event‑Driven Pipeline** – Decoupled stages with Redis/ BullMQ
- 📈 **Comprehensive Observability** – Prometheus metrics, OpenTelemetry tracing, structured logs
- 🧪 **Test Coverage >90%** – Unit, integration, E2E, performance, and security tests

---

## 🏗️ Architecture

Clean Architecture + Hexagonal (Ports & Adapters) + Domain‑Driven Design.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERFACES (FastAPI)                       │
│                    (Controllers, Schemas, Middleware)               │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                      APPLICATION (Use Cases)                       │
│                   (Orchestrates Domain via Ports)                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         ENGINE (Pipeline)                          │
│         (Validation → Context → Risk → Confidence → Priority)       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                        DOMAIN (Core Logic)                         │
│        (Entities, Value Objects, Pure Services, Interfaces)         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                        CORE (Cross-Cutting)                        │
│           (Config, Constants, Exceptions, Logging, DI)              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                    INFRASTRUCTURE (Adapters)                       │
│        (Persistence, Cache, External APIs, Messaging)               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Technology Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Web Framework | FastAPI |
| Architecture | Clean + Hexagonal + DDD |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL / SQLite (dev) |
| Migration | Alembic |
| Cache & Messaging | Redis / Upstash |
| Logging | Structlog |
| LLM Integration | Groq, OpenAI, Gemini, Ollama |
| Testing | Pytest, coverage, benchmark |
| Dependency Management | Poetry |

---

## 🛠️ Installation

### Prerequisites

- Python 3.11+
- Poetry (or pip)
- PostgreSQL (optional, SQLite works for development)
- Redis (optional, MemoryCache works for development)

### Clone and Install

```bash
git clone https://github.com/saketanalyst-eng/quatiquen_ai_engine_repo.git
cd quatiquen_ai_engine_repo

# Install dependencies via Poetry
poetry install

# Or using pip + requirements.txt
pip install -r requirements.txt
```

### Environment Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` – at minimum, set `DATABASE_URL` and (optionally) `GROQ_API_KEY`.

---

## 🗄️ Database Setup

Run migrations and seed the knowledge base:

```bash
# With Poetry
poetry run migrate
poetry run seed

# Or using direct commands
python -m scripts.run_migrations
python -m scripts.seed_knowledge_base
```

> For SQLite, the database file `quantiquan.db` will be created automatically.  
> For PostgreSQL, ensure the database exists and credentials are correct.

---

## ▶️ Running the Server

```bash
# With Poetry
poetry run quantiquan

# Or manually
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.  
Swagger UI (if `debug=true`) is at `/docs`.

---

## 🧪 Running Tests

```bash
# All tests with coverage
poetry run pytest

# Specific categories
poetry run pytest tests/unit/
poetry run pytest tests/integration/
poetry run pytest tests/e2e/
poetry run pytest tests/performance/ --benchmark-only
```

Coverage report is generated in `htmlcov/`.

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Service health check |
| `/api/v1/readiness` | GET | Readiness probe |
| `/api/v1/risk/calculate` | POST | Score a new finding |
| `/api/v1/risk/{finding_id}` | GET | Retrieve a decision |
| `/api/v1/risk/recalculate` | POST | Re‑score a finding |

### Example Request – Risk Calculation

```json
POST /api/v1/risk/calculate
{
  "tenant_id": "11111111-1111-1111-1111-111111111111",
  "asset_id": "22222222-2222-2222-2222-222222222222",
  "source": "internal_scanner",
  "source_finding_id": "scan-123",
  "title": "Critical vulnerability in payment API",
  "description": "Unpatched RCE vulnerability in payment gateway",
  "raw_severity": 8.5,
  "raw_severity_scale": "cvss_v3",
  "detected_at": 1690000000,
  "raw_payload": {"scanner": "test", "details": "..."},
  "cve_id": "CVE-2024-12345",
  "status": "open"
}
```

### Example Response

```json
{
  "finding_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "11111111-1111-1111-1111-111111111111",
  "bis": 85.0,
  "tier": "Critical",
  "confidence": 0.9,
  "drivers": {
    "asset_importance": 95,
    "vulnerability_severity": 72,
    "exploitability": 92,
    "business_impact": 90,
    "exposure": 85
  },
  "recommendation_id": null,
  "summary": "This vulnerability affects your production payment system, which handles regulated data. Immediate action is recommended.",
  "computed_at": 1690000000
}
```

---

## 🧠 AI Summary

The engine can generate a plain‑language business explanation via LLM providers:

- **Groq** (primary, fast)
- **OpenAI** (fallback)
- **Gemini** (fallback)
- **Ollama** (local)

Set `GROQ_API_KEY` in `.env` for real summaries.  
If no key is provided, a sensible mock is returned (so the pipeline still works).

---

## 📁 Project Structure

```
quantiquan-ai-engine/
├── src/                 # Source code (Clean Architecture)
│   ├── core/           # Cross-cutting concerns
│   ├── domain/         # Entities, value objects, pure services
│   ├── application/    # Use cases, DTOs, ports
│   ├── engine/         # Scoring pipeline orchestration
│   ├── ai/             # LLM integration
│   ├── infrastructure/ # Persistence, cache, external clients
│   ├── interfaces/     # FastAPI routes, schemas, middleware
│   ├── knowledge_base/ # Static JSON data
│   └── utils/          # Helpers
├── tests/              # Unit, integration, e2e, performance, security
├── scripts/            # Migration and seeding
├── pyproject.toml      # Poetry config
├── Makefile            # Common tasks
├── .env.example        # Environment template
└── README.md           # You are here
```

---

## 🐳 Deployment

### Docker

A Dockerfile is provided in the repository. Build and run:

```bash
docker build -t quantiquan-ai-engine .
docker run -p 8000:8000 --env-file .env quantiquan-ai-engine
```

### Manual (Production)

- Set `ENV_STATE=production` in `.env`.
- Use a production PostgreSQL database and Redis.
- Run with `uvicorn` without `--reload` and behind a reverse proxy (nginx / Traefik).

---

## 🤝 Contributing

Contributions are welcome!  
Please open an issue or pull request. Make sure to:

- Follow the existing code style (`black`, `isort`, `ruff`)
- Write tests for new features
- Update documentation

---

## 📄 License

This project is proprietary and confidential.  
All rights reserved.

---

## 📬 Support

For issues, questions, or feedback, please open a GitHub issue or contact the maintainers.

---

**Built with ❤️ by the QUANTIQUAN Team**
```

---

### ✅ Save This File

Replace your existing `README.md` with the content above, commit and push:

```bash
git add README.md
git commit -m "docs: add comprehensive README"
git push
```

Now your repository is fully documented and ready for collaboration. 🚀
