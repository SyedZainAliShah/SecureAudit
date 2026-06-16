# SecureAudit

**AI-powered OWASP Top 10 & GDPR compliance checker — runs entirely locally.**

Paste code, drop a file, or point it at a public GitHub repo. SecureAudit streams findings in real time using a local LLM (Ollama), saves every audit to a database, and lets you track risk trends over time.

![CI](https://github.com/SyedZainAliShah/SecureAudit/actions/workflows/ci.yml/badge.svg)

---

## Features

- **Three input modes** — paste a code snippet, upload a file (.py .js .ts .java and more), or enter a public GitHub repo URL
- **Real-time streaming** — findings appear one by one as the LLM generates them via SSE
- **OWASP Top 10 (2021)** — injection, broken auth, cryptographic failures, XSS, SSRF, and more
- **GDPR compliance** — data minimisation, right to erasure, consent, PII exposure (Art. 5/9/17/25/32)
- **Audit history** — every report saved to SQLite (local) or PostgreSQL (Docker), searchable and filterable
- **Analytics dashboard** — severity breakdown chart, risk score trend across last 10 audits
- **PDF export** — one-click print-to-PDF with a dedicated print stylesheet
- **Re-run audits** — tweak checks and re-run with one click from the report view
- **100% local** — no data leaves your machine; no API keys required

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Angular 19 (standalone components, SSE streaming) |
| Backend | FastAPI (Python 3.12), async SQLAlchemy 2.0 |
| LLM | Ollama (llama3) — runs locally |
| Database | SQLite (dev) / PostgreSQL (Docker) |
| Charts | Chart.js |
| Containers | Docker Compose (3 services) |
| CI | GitHub Actions |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 22+
- [Ollama](https://ollama.com) installed and running

### 1. Pull the model

```bash
ollama pull llama3
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
# API at http://localhost:8000  |  Swagger docs: http://localhost:8000/docs
```

### 3. Frontend

```bash
cd frontend/secure-audit
npm install
ng serve
# App at http://localhost:4200
```

---

## Docker Compose (Full Stack)

```bash
docker compose up --build
# App at http://localhost:80
```

> Ollama must be running on the host machine. The backend reaches it via `host.docker.internal:11434`.

---

## Running Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx
python -m pytest tests/ -v
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Browser (Angular 19)                                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Audit Form │  │ Audit Report │  │ History/Analytics│   │
│  │ code/file/  │  │ risk ring    │  │ Chart.js         │   │
│  │ github URL  │  │ PDF export   │  │ search & filter  │   │
│  └──────┬──────┘  └──────────────┘  └──────────────────┘   │
└─────────┼────────────────────────────────────────────────────┘
          │ SSE / HTTP
┌─────────▼───────────────────────────────────────────────────┐
│  FastAPI Backend                                             │
│  POST /audit/stream  →  analyzer.py  →  Ollama (llama3)    │
│  POST /github-fetch  →  GitHub API  →  file concat          │
│  GET  /audits        →  SQLAlchemy  →  SQLite / PostgreSQL  │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
SecureAudit/
├── backend/
│   ├── main.py          # FastAPI routes
│   ├── analyzer.py      # Ollama prompt + streaming + JSON extraction
│   ├── database.py      # SQLAlchemy async engine
│   ├── db_models.py     # AuditRecord ORM model
│   ├── models.py        # Pydantic models
│   ├── tests/           # pytest suite
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/secure-audit/
│   ├── src/app/
│   │   ├── components/
│   │   │   ├── audit-form/      # Code / GitHub / file upload input
│   │   │   ├── audit-report/    # Report with PDF export & re-run
│   │   │   ├── finding-card/    # Expandable finding detail
│   │   │   ├── audit-history/   # History list with search & filter
│   │   │   └── audit-chart/     # Chart.js severity & trend charts
│   │   ├── services/audit.service.ts
│   │   └── models/audit.models.ts
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── .github/workflows/ci.yml
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Ollama connectivity check |
| `POST` | `/audit` | Run audit (non-streaming) |
| `POST` | `/audit/stream` | Run audit (SSE streaming) |
| `POST` | `/github-fetch` | Fetch public GitHub repo files |
| `GET` | `/audits` | List audit history |
| `GET` | `/audits/{id}` | Get single report |
| `DELETE` | `/audits/{id}` | Delete audit |

---

## Changing the Model

In `backend/analyzer.py`:

```python
OLLAMA_MODEL = "llama3"   # swap for "mistral", "gemma2", "codellama", etc.
```

---

## Why I Built This

SecureAudit combines my professional background in cybersecurity (UEBA, GDPR/CCPA compliance tooling at GhangorCloud) with my M.Sc. coursework in IT Security and Cryptography at Philipps-Universität Marburg. The GDPR analysis is particularly relevant for the German and European market, where privacy-by-design is a legal requirement rather than an afterthought.

---

Built by [@SyedZainAliShah](https://github.com/SyedZainAliShah) · Angular + FastAPI + Ollama · MIT License
