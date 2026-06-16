import httpx
import json
import re
from models import AuditRequest, AuditReport, Finding

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"   # change to "mistral" or any model you have pulled


OWASP_CONTEXT = """
OWASP Top 10 (2021) categories to check for:
- A01: Broken Access Control
- A02: Cryptographic Failures (weak encryption, sensitive data in plaintext, hardcoded secrets)
- A03: Injection (SQL, NoSQL, command injection, XSS)
- A04: Insecure Design
- A05: Security Misconfiguration (default credentials, verbose errors, unnecessary features)
- A06: Vulnerable and Outdated Components
- A07: Identification and Authentication Failures (weak passwords, missing MFA, insecure session management)
- A08: Software and Data Integrity Failures
- A09: Security Logging and Monitoring Failures
- A10: Server-Side Request Forgery (SSRF)
"""

GDPR_CONTEXT = """
GDPR compliance principles to check for:
- Art. 5: Lawfulness, fairness, transparency — is data collection justified?
- Art. 5: Purpose limitation — data used only for stated purpose?
- Art. 5: Data minimisation — only necessary data collected?
- Art. 5: Storage limitation — data retained longer than necessary?
- Art. 25: Privacy by design and by default
- Art. 32: Security of processing — appropriate technical measures (encryption, pseudonymisation)?
- Art. 33/34: Breach notification readiness
- Art. 13/14: Information obligations — users informed about data usage?
- Art. 17: Right to erasure — can users delete their data?
- Special categories (Art. 9): Extra protection for health, biometric, political data
"""


def build_prompt(req: AuditRequest) -> str:
    check_sections = []
    if "owasp" in req.checks:
        check_sections.append(OWASP_CONTEXT)
    if "gdpr" in req.checks:
        check_sections.append(GDPR_CONTEXT)

    input_description = (
        f"the following {req.language} code"
        if req.input_type == "code"
        else "the following system/feature description"
    )

    return f"""You are a senior security and compliance auditor. Analyze {input_description} and identify security vulnerabilities and compliance issues.

{chr(10).join(check_sections)}

INPUT TO ANALYZE:
```
{req.input}
```

Return ONLY a valid JSON object with this exact structure (no markdown, no explanation outside the JSON):
{{
  "summary": "2-3 sentence executive summary of the overall risk posture",
  "risk_score": <integer 0-100, where 0=no risk, 100=critical>,
  "findings": [
    {{
      "id": "F001",
      "category": "<OWASP category or GDPR article>",
      "title": "<short title>",
      "severity": "<critical|high|medium|low|info>",
      "description": "<what the issue is and why it matters>",
      "recommendation": "<specific actionable fix>",
      "line_reference": "<line numbers if applicable, otherwise null>"
    }}
  ],
  "checks_performed": {json.dumps(req.checks)},
  "input_type": "{req.input_type}"
}}

Rules:
- Only report real issues you can identify. Do not invent findings.
- If no issues found in a category, do not add a finding for it.
- severity must be one of: critical, high, medium, low, info
- risk_score should reflect the worst finding (critical=80-100, high=60-79, medium=40-59, low=20-39, all info=0-19)
- Return valid JSON only. No markdown fences. No text before or after the JSON.
"""


def extract_json(text: str) -> dict:
    """Extract JSON from model output even if it has extra text."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to find JSON block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from model output:\n{text[:500]}")


async def run_audit(req: AuditRequest) -> AuditReport:
    prompt = build_prompt(req)

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,   # low temp = more deterministic, better for structured output
                "num_predict": 2048,
            }
        })
        response.raise_for_status()

    raw = response.json().get("response", "")
    data = extract_json(raw)

    # Validate and build findings
    findings = [Finding(**f) for f in data.get("findings", [])]

    return AuditReport(
        summary=data["summary"],
        risk_score=int(data["risk_score"]),
        findings=findings,
        checks_performed=data.get("checks_performed", req.checks),
        input_type=req.input_type,
    )
