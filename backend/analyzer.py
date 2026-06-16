import httpx
import json
import re
from typing import AsyncGenerator
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


SECRETS_CONTEXT = """
Secret Detection — check for hardcoded sensitive values:
- Hardcoded passwords, API keys, tokens, or secrets in source code
- Private keys or certificates embedded in code
- Database connection strings with credentials
- AWS/GCP/Azure access keys or secrets
- JWT secrets or signing keys
- OAuth client secrets
- Any string matching patterns like: password=, secret=, api_key=, token=, private_key=
- Credentials in config files, .env files committed to code, or default credentials left in place
"""

PCI_DSS_CONTEXT = """
PCI DSS (Payment Card Industry Data Security Standard) — check for:
- Req 3: Cardholder data (PAN, CVV, expiry) stored unencrypted or logged
- Req 3: Full card numbers visible in logs, error messages, or API responses
- Req 4: Cardholder data transmitted without TLS/encryption
- Req 6: Vulnerable functions used in payment flows (SQL injection, XSS vectors)
- Req 7/8: Missing access controls or authentication on payment endpoints
- Req 10: Insufficient audit logging for payment transactions
- Req 6.4: Hardcoded credentials or default passwords in payment systems
- Any storage or logging of CVV/CVC/CVV2, magnetic stripe data, or PIN blocks
"""

HIPAA_CONTEXT = """
HIPAA (Health Insurance Portability and Accountability Act) — check for:
- PHI (Protected Health Information) stored without encryption: names, DOB, SSN, diagnosis, medications, health records
- PHI transmitted without TLS or over unencrypted channels
- Missing access controls or audit logging on endpoints handling health data
- PHI logged in application logs, error messages, or debug output
- Insufficient de-identification of health data
- Missing data retention and destruction policies in code
- No minimum necessary principle — accessing more PHI than required for the function
- Missing Business Associate Agreement indicators in third-party data sharing
- Health data exposed in API responses without role-based access control
"""


def build_prompt(req: AuditRequest) -> str:
    check_sections = []
    if "owasp" in req.checks:
        check_sections.append(OWASP_CONTEXT)
    if "gdpr" in req.checks:
        check_sections.append(GDPR_CONTEXT)
    if "secrets" in req.checks:
        check_sections.append(SECRETS_CONTEXT)
    if "pci" in req.checks:
        check_sections.append(PCI_DSS_CONTEXT)
    if "hipaa" in req.checks:
        check_sections.append(HIPAA_CONTEXT)

    input_description = (
        f"the following {req.language} code"
        if req.input_type == "code"
        else "the following system/feature description"
    )

    return f"""<SYSTEM>You are a JSON API. You output only raw JSON. You never write explanations, preambles, or markdown. Your entire response must be a single valid JSON object starting with {{ and ending with }}.</SYSTEM>

Analyze {input_description} for security vulnerabilities and compliance issues.

{chr(10).join(check_sections)}

INPUT:
{req.input}

OUTPUT (raw JSON only, nothing else):
{{
  "summary": "2-3 sentence executive summary",
  "risk_score": <integer 0-100: 85-100 if critical findings, 60-84 if high, 35-59 if medium, 10-34 if low, 0-9 if info only>,
  "findings": [
    {{
      "id": "F001",
      "category": "<OWASP category or GDPR article>",
      "title": "<short title>",
      "severity": "<critical|high|medium|low|info>",
      "description": "<what the issue is>",
      "recommendation": "<specific fix>",
      "line_reference": "<line numbers or null>"
    }}
  ],
  "checks_performed": {json.dumps(req.checks)},
  "input_type": "{req.input_type}"
}}"""


def extract_json(text: str) -> dict:
    """Extract JSON from model output even if it has extra text."""
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Find the outermost { ... } by bracket matching
    start = text.find('{')
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    candidate = text[start:i+1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    # Last resort: truncated JSON — close any open brackets and retry
    if start != -1:
        fragment = text[start:]
        open_braces = fragment.count('{') - fragment.count('}')
        open_brackets = fragment.count('[') - fragment.count(']')
        # Remove the last incomplete object (find last complete finding)
        last_complete = fragment.rfind('},')
        if last_complete != -1:
            fragment = fragment[:last_complete + 1]
            fragment += ']' * max(open_brackets - 1, 0)
            fragment += '}' * max(open_braces - 1, 0)
            fragment = fragment.rstrip(',') + ']}'
            try:
                return json.loads(fragment)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Could not extract valid JSON from model output: {text[:300]}")


async def run_audit(req: AuditRequest) -> AuditReport:
    """Non-streaming audit — waits for full response."""
    prompt = build_prompt(req)

    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": -1},
        })
        response.raise_for_status()

    raw = response.json().get("response", "")
    data = extract_json(raw)
    findings = [Finding(**f) for f in data.get("findings", [])]

    return AuditReport(
        summary=data["summary"],
        risk_score=int(data["risk_score"]),
        findings=findings,
        checks_performed=data.get("checks_performed", req.checks),
        input_type=req.input_type,
    )


async def stream_audit(req: AuditRequest) -> AsyncGenerator[str, None]:
    """
    Streaming audit using SSE.
    Yields server-sent event strings.
    Emits:
      - status events while Ollama is generating
      - finding events as each finding is parsed
      - complete event with the full report
      - error event on failure
    """
    prompt = build_prompt(req)

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    yield sse("status", {"message": "Connecting to Ollama...", "progress": 5})

    collected = ""
    token_count = 0

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {"temperature": 0.1, "num_predict": -1},
            }) as response:
                response.raise_for_status()

                yield sse("status", {"message": "Analyzing your code...", "progress": 15})

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        collected += token
                        token_count += 1

                        # Emit progress every 50 tokens
                        if token_count % 50 == 0:
                            progress = min(15 + int((token_count / 800) * 60), 75)
                            yield sse("status", {"message": "Identifying vulnerabilities...", "progress": progress})

                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

        yield sse("status", {"message": "Parsing findings...", "progress": 80})

        data = extract_json(collected)
        findings = [Finding(**f) for f in data.get("findings", [])]

        # Stream each finding individually for dramatic effect
        for i, finding in enumerate(findings):
            yield sse("finding", {
                "finding": finding.model_dump(),
                "index": i,
                "total": len(findings),
            })

        yield sse("status", {"message": "Finalising report...", "progress": 95})

        report = AuditReport(
            summary=data["summary"],
            risk_score=int(data["risk_score"]),
            findings=findings,
            checks_performed=data.get("checks_performed", req.checks),
            input_type=req.input_type,
        )

        yield sse("complete", {"report": report.model_dump()})

    except Exception as e:
        yield sse("error", {"message": str(e)})
