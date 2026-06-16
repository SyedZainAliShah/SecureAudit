from pydantic import BaseModel
from typing import Literal, List


class AuditRequest(BaseModel):
    input: str
    input_type: Literal["code", "description"] = "code"
    language: str = "python"  # programming language if code
    checks: List[Literal["owasp", "gdpr"]] = ["owasp", "gdpr"]


class Finding(BaseModel):
    id: str
    category: str          # e.g. "A03 - Injection" or "GDPR Art. 5"
    title: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    description: str
    recommendation: str
    line_reference: str | None = None   # e.g. "Line 12-15" if applicable


class AuditReport(BaseModel):
    summary: str
    risk_score: int           # 0-100
    findings: List[Finding]
    checks_performed: List[str]
    input_type: str
