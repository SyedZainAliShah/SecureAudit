export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type InputType = 'code' | 'description';
export type CheckType = 'owasp' | 'gdpr';

export interface AuditRequest {
  input: string;
  input_type: InputType;
  language: string;
  checks: CheckType[];
}

export interface Finding {
  id: string;
  category: string;
  title: string;
  severity: Severity;
  description: string;
  recommendation: string;
  line_reference: string | null;
}

export interface AuditReport {
  summary: string;
  risk_score: number;
  findings: Finding[];
  checks_performed: string[];
  input_type: string;
}
