from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx

from models import AuditRequest, AuditReport
from analyzer import run_audit, OLLAMA_URL, OLLAMA_MODEL

app = FastAPI(
    title="SecureAudit API",
    description="AI-powered OWASP & GDPR compliance checker powered by Ollama",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Angular dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Check API and Ollama connectivity."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        return {"status": "ok", "ollama": "connected", "available_models": models}
    except Exception as e:
        return {"status": "degraded", "ollama": "unreachable", "error": str(e)}


@app.post("/audit", response_model=AuditReport)
async def audit(req: AuditRequest):
    """
    Run an OWASP / GDPR audit on submitted code or system description.

    - **input**: the code snippet or system description to analyze
    - **input_type**: `code` or `description`
    - **language**: programming language (used when input_type is code)
    - **checks**: list of checks to run — `owasp`, `gdpr`, or both
    """
    if not req.input.strip():
        raise HTTPException(status_code=422, detail="Input cannot be empty.")
    if len(req.input) > 8000:
        raise HTTPException(status_code=422, detail="Input too long. Maximum 8000 characters.")

    try:
        report = await run_audit(req)
        return report
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama. Make sure Ollama is running: `ollama serve`"
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")
