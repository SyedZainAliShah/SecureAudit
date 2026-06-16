"""
SecureAudit API tests.
Run with: cd backend && python -m pytest tests/ -v
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from main import app
from models import AuditReport, Finding


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_report():
    return AuditReport(
        id=1,
        summary="Test report with SQL injection vulnerability.",
        risk_score=75,
        findings=[
            Finding(
                id="F001",
                category="A03: Injection",
                title="SQL Injection",
                severity="high",
                description="User input is directly interpolated into SQL queries.",
                recommendation="Use parameterised queries or an ORM.",
                line_reference="line 12",
            )
        ],
        checks_performed=["owasp", "gdpr"],
        input_type="code",
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_db():
    """Mock AsyncSession so tests don't need a real database."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"models": [{"name": "llama3"}]}
        )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


# ── Input validation ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_rejects_empty_input():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/audit", json={
            "input": "",
            "input_type": "code",
            "language": "python",
            "checks": ["owasp"],
        })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_audit_rejects_input_over_8000_chars():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/audit", json={
            "input": "x" * 8001,
            "input_type": "code",
            "language": "python",
            "checks": ["owasp"],
        })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_github_fetch_rejects_invalid_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/github-fetch", json={"url": "not-a-github-url"})
    assert resp.status_code == 422


# ── JSON extraction ───────────────────────────────────────────────────────────

def test_extract_json_parses_clean_json():
    from analyzer import extract_json
    raw = '{"summary": "ok", "risk_score": 50, "findings": []}'
    result = extract_json(raw)
    assert result["risk_score"] == 50


def test_extract_json_strips_preamble():
    from analyzer import extract_json
    raw = 'Here is the JSON output: {"summary": "ok", "risk_score": 30, "findings": []}'
    result = extract_json(raw)
    assert result["risk_score"] == 30


def test_extract_json_strips_markdown_fences():
    from analyzer import extract_json
    raw = '```json\n{"summary": "ok", "risk_score": 20, "findings": []}\n```'
    result = extract_json(raw)
    assert result["risk_score"] == 20


def test_extract_json_raises_on_garbage():
    from analyzer import extract_json
    import pytest
    with pytest.raises(ValueError):
        extract_json("This is not JSON at all.")


# ── GitHub URL parser ─────────────────────────────────────────────────────────

def test_parse_github_url_standard():
    from main import _parse_github_url
    owner, repo = _parse_github_url("https://github.com/SyedZainAliShah/SecureAudit")
    assert owner == "SyedZainAliShah"
    assert repo == "SecureAudit"


def test_parse_github_url_with_trailing_slash():
    from main import _parse_github_url
    owner, repo = _parse_github_url("https://github.com/owner/repo/")
    assert owner == "owner"
    assert repo == "repo"


def test_parse_github_url_invalid():
    from main import _parse_github_url
    with pytest.raises(ValueError):
        _parse_github_url("https://gitlab.com/owner/repo")


# ── Risk label logic ──────────────────────────────────────────────────────────

def test_detect_language_python(tmp_path):
    from main import _detect_language
    assert _detect_language(["main.py", "utils.py", "app.py"]) == "python"


def test_detect_language_typescript():
    from main import _detect_language
    assert _detect_language(["app.ts", "service.ts", "component.ts"]) == "typescript"
