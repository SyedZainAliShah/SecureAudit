from pydantic import BaseModel
from typing import Literal, List, Optional
from datetime import datetime


class AuditRequest(BaseModel):
    input: str
    input_type: Literal["code", "description"] = "code"
    language: str = "python"
    checks: List[Literal["owasp", "gdpr", "secrets", "pci", "hipaa"]] = ["owasp", "gdpr"]


class GitHubFetchRequest(BaseModel):
    url: str


class GitHubFetchResponse(BaseModel):
    content: str
    language: str
    files_fetched: List[str]
    repo: str
    truncated: bool = False


class Finding(BaseModel):
    id: str
    category: str
    title: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    description: str
    recommendation: str
    line_reference: Optional[str] = None


class AuditReport(BaseModel):
    id: Optional[int] = None
    summary: str
    risk_score: int
    findings: List[Finding]
    checks_performed: List[str]
    input_type: str
    created_at: Optional[datetime] = None


class AuditSummary(BaseModel):
    """Lightweight record for history list."""
    id: int
    created_at: datetime
    input_type: str
    language: Optional[str]
    checks_performed: List[str]
    risk_score: int
    summary: str
    input_preview: str
    finding_counts: dict  # {"critical": 0, "high": 2, ...}
