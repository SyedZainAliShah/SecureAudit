from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import httpx

from models import AuditRequest, AuditReport, AuditSummary, GitHubFetchRequest, GitHubFetchResponse
from analyzer import run_audit, stream_audit, OLLAMA_URL
from database import init_db, get_db
from db_models import AuditRecord

app = FastAPI(
    title="SecureAudit API",
    description="AI-powered OWASP & GDPR compliance checker powered by Ollama",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        return {"status": "ok", "ollama": "connected", "available_models": models}
    except Exception as e:
        return {"status": "degraded", "ollama": "unreachable", "error": str(e)}


# ── Audit (non-streaming) ───────────────────────────────────────────────────

@app.post("/audit", response_model=AuditReport)
async def audit(req: AuditRequest, db: AsyncSession = Depends(get_db)):
    if not req.input.strip():
        raise HTTPException(status_code=422, detail="Input cannot be empty.")
    if len(req.input) > 8000:
        raise HTTPException(status_code=422, detail="Input too long. Maximum 8000 characters.")

    try:
        report = await run_audit(req)
        record = await _save_audit(db, req, report)
        report.id = record.id
        report.created_at = record.created_at
        return report
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama.")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


# ── Audit (streaming SSE) ───────────────────────────────────────────────────

@app.post("/audit/stream")
async def audit_stream(req: AuditRequest, db: AsyncSession = Depends(get_db)):
    if not req.input.strip():
        raise HTTPException(status_code=422, detail="Input cannot be empty.")
    if len(req.input) > 8000:
        raise HTTPException(status_code=422, detail="Input too long.")

    async def event_generator():
        report_data = None
        async for event in stream_audit(req):
            yield event
            # Capture the complete report from the last SSE event
            if event.startswith("event: complete"):
                import json
                data_line = event.split("data: ", 1)[1].strip()
                try:
                    report_data = json.loads(data_line).get("report")
                except Exception:
                    pass

        # Save to DB after streaming completes
        if report_data:
            try:
                report = AuditReport(**report_data)
                record = await _save_audit(db, req, report)
                import json
                yield f"event: saved\ndata: {json.dumps({'id': record.id})}\n\n"
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── GitHub Fetch ─────────────────────────────────────────────────────────────

GITHUB_CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.go', '.rb', '.php',
    '.cs', '.cpp', '.c', '.h', '.rs', '.kt', '.swift',
    '.jsx', '.tsx', '.vue', '.sh', '.yaml', '.yml', '.tf',
}
SKIP_DIRS = {'node_modules', '.git', 'dist', 'build', '__pycache__', 'vendor', '.venv', 'venv'}

def _parse_github_url(url: str) -> tuple[str, str]:
    """Extract owner and repo from a GitHub URL."""
    import re
    url = url.strip().rstrip('/')
    match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
    if not match:
        raise ValueError("Invalid GitHub URL. Expected: https://github.com/owner/repo")
    return match.group(1), match.group(2).removesuffix('.git')

def _detect_language(files: list[str]) -> str:
    from collections import Counter
    exts = Counter(f.rsplit('.', 1)[-1] for f in files if '.' in f)
    ext_map = {
        'py': 'python', 'js': 'javascript', 'ts': 'typescript',
        'java': 'java', 'go': 'go', 'rb': 'ruby', 'php': 'php',
        'cs': 'csharp', 'cpp': 'cpp', 'rs': 'rust', 'kt': 'kotlin',
    }
    for ext, _ in exts.most_common():
        if ext in ext_map:
            return ext_map[ext]
    return 'other'

@app.post("/github-fetch", response_model=GitHubFetchResponse)
async def github_fetch(payload: GitHubFetchRequest):
    try:
        owner, repo = _parse_github_url(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        # Get the default branch
        repo_resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
        if repo_resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Repository not found or is private.")
        if repo_resp.status_code == 403:
            raise HTTPException(status_code=429, detail="GitHub API rate limit hit. Try again in a minute.")
        repo_resp.raise_for_status()
        default_branch = repo_resp.json().get("default_branch", "main")

        # Get file tree
        tree_resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        )
        tree_resp.raise_for_status()
        tree = tree_resp.json().get("tree", [])

    # Filter to code files, skip large/generated dirs
    code_files = [
        item["path"] for item in tree
        if item["type"] == "blob"
        and any(item["path"].endswith(ext) for ext in GITHUB_CODE_EXTENSIONS)
        and not any(skip in item["path"].split('/') for skip in SKIP_DIRS)
        and item.get("size", 99999) < 50000  # skip huge files
    ]

    if not code_files:
        raise HTTPException(status_code=422, detail="No supported code files found in this repository.")

    # Fetch file contents up to 7500 chars total
    fetched_files = []
    parts = []
    total_chars = 0
    truncated = False

    async with httpx.AsyncClient(timeout=15.0) as client:
        for path in code_files[:30]:  # cap at 30 files
            if total_chars >= 7000:
                truncated = True
                break
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{path}"
            r = await client.get(raw_url)
            if r.status_code != 200:
                continue
            content = r.text[:2000]  # cap each file at 2000 chars
            part = f"// FILE: {path}\n{content}\n"
            if total_chars + len(part) > 7500:
                truncated = True
                break
            parts.append(part)
            fetched_files.append(path)
            total_chars += len(part)

    if not parts:
        raise HTTPException(status_code=422, detail="Could not fetch any file contents.")

    return GitHubFetchResponse(
        content="\n".join(parts),
        language=_detect_language(fetched_files),
        files_fetched=fetched_files,
        repo=f"{owner}/{repo}",
        truncated=truncated,
    )


# ── History ─────────────────────────────────────────────────────────────────

@app.get("/audits", response_model=list[AuditSummary])
async def list_audits(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditRecord).order_by(desc(AuditRecord.created_at)).limit(limit)
    )
    records = result.scalars().all()
    return [_record_to_summary(r) for r in records]


@app.get("/audits/{audit_id}", response_model=AuditReport)
async def get_audit(audit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditRecord).where(AuditRecord.id == audit_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Audit not found.")
    return _record_to_report(record)


@app.delete("/audits/{audit_id}", status_code=204)
async def delete_audit(audit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditRecord).where(AuditRecord.id == audit_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Audit not found.")
    await db.delete(record)
    await db.commit()


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _save_audit(db: AsyncSession, req: AuditRequest, report: AuditReport) -> AuditRecord:
    record = AuditRecord(
        input_type=req.input_type,
        language=req.language,
        checks_performed=report.checks_performed,
        risk_score=report.risk_score,
        summary=report.summary,
        findings=[f.model_dump() for f in report.findings],
        input_preview=req.input[:200],
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


def _record_to_summary(r: AuditRecord) -> AuditSummary:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in (r.findings or []):
        sev = f.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1
    return AuditSummary(
        id=r.id,
        created_at=r.created_at,
        input_type=r.input_type,
        language=r.language,
        checks_performed=r.checks_performed,
        risk_score=r.risk_score,
        summary=r.summary,
        input_preview=r.input_preview,
        finding_counts=counts,
    )


def _record_to_report(r: AuditRecord) -> AuditReport:
    from models import Finding
    return AuditReport(
        id=r.id,
        created_at=r.created_at,
        summary=r.summary,
        risk_score=r.risk_score,
        findings=[Finding(**f) for f in (r.findings or [])],
        checks_performed=r.checks_performed,
        input_type=r.input_type,
    )
