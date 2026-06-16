# 🔐 SecureAudit — AI-Powered OWASP & GDPR Compliance Checker

SecureAudit analyzes code snippets and system descriptions for security vulnerabilities and GDPR compliance gaps using a locally-running LLM (via Ollama). No data leaves your machine.

![SecureAudit Demo](./docs/demo.png)

## Features

- **OWASP Top 10 detection** — SQL injection, XSS, broken auth, cryptographic failures, SSRF, and more
- **GDPR compliance analysis** — data minimisation, storage limitation, privacy by design, breach readiness (Articles 5, 25, 32)
- **Risk scoring** — 0–100 risk score with severity-grouped findings (Critical / High / Medium / Low / Info)
- **Click-to-expand findings** — each finding shows the issue + a specific, actionable recommendation
- **Copy as Markdown** — export any report to clipboard for documentation or tickets
- **Load example** — one-click demo with a Python Flask snippet containing intentional vulnerabilities
- **100% local** — powered by Ollama; no API keys required, no data sent externally

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Angular 19 (standalone components, signals) |
| Backend | FastAPI (Python) |
| LLM | Ollama (llama3 / mistral / any local model) |
| Styling | SCSS with CSS variables (dark theme) |

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [Python](https://python.org/) 3.11+
- [Ollama](https://ollama.com/) installed and running

### 1. Pull an Ollama model

```bash
ollama pull llama3
# or: ollama pull mistral
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.  
Swagger docs: `http://localhost:8000/docs`

### 3. Start the frontend

```bash
cd frontend/secure-audit
npm install
ng serve
```

Open `http://localhost:4200` in your browser.

## Project Structure

```
SecureAudit/
├── backend/
│   ├── main.py          # FastAPI app & endpoints
│   ├── analyzer.py      # Ollama integration & prompt engineering
│   ├── models.py        # Pydantic request/response models
│   └── requirements.txt
│
└── frontend/secure-audit/
    └── src/app/
        ├── components/
        │   ├── audit-form/      # Input form (code or description)
        │   ├── audit-report/    # Results view with risk score ring
        │   └── finding-card/    # Expandable finding component
        ├── models/
        │   └── audit.models.ts  # TypeScript interfaces
        └── services/
            └── audit.service.ts # HTTP client for backend API
```

## How It Works

1. User pastes code or describes a system in the Angular frontend
2. Selects which checks to run: OWASP Top 10, GDPR, or both
3. Angular sends a `POST /audit` request to the FastAPI backend
4. FastAPI builds a structured prompt with OWASP/GDPR context and sends it to the local Ollama model
5. The model returns a JSON audit report — findings with severity, description, and recommendations
6. The frontend renders the report with a risk score ring, filterable findings, and expand/collapse detail

## API Reference

### `POST /audit`

```json
{
  "input": "<code or system description>",
  "input_type": "code",
  "language": "python",
  "checks": ["owasp", "gdpr"]
}
```

**Response:**
```json
{
  "summary": "The submitted code contains several critical vulnerabilities...",
  "risk_score": 85,
  "findings": [
    {
      "id": "F001",
      "category": "A03 - Injection",
      "title": "SQL Injection via string interpolation",
      "severity": "critical",
      "description": "User input is directly interpolated into SQL queries...",
      "recommendation": "Use parameterized queries or an ORM...",
      "line_reference": "Line 12-14"
    }
  ],
  "checks_performed": ["owasp", "gdpr"],
  "input_type": "code"
}
```

### `GET /health`

Returns Ollama connectivity status and available models.

## Changing the Model

Open `backend/analyzer.py` and update:

```python
OLLAMA_MODEL = "llama3"   # change to "mistral", "gemma2", etc.
```

## Why I Built This

I built SecureAudit to demonstrate applied LLM usage in a real-world security context, combining my professional background in cybersecurity (UEBA, GDPR/CCPA compliance tools at GhangorCloud) with my M.Sc. coursework in IT Security and Cryptography at Philipps-Universität Marburg.

The GDPR analysis is particularly relevant for the German and European market, where privacy-by-design is a legal requirement, not an afterthought.

## License

MIT
