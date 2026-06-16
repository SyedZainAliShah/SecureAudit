export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type InputType = 'code' | 'description' | 'github';

export interface GitHubFetchResponse {
  content: string;
  language: string;
  files_fetched: string[];
  repo: string;
  truncated: boolean;
}
export type CheckType = 'owasp' | 'gdpr' | 'secrets' | 'pci' | 'hipaa';

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
  id?: number;
  summary: string;
  risk_score: number;
  findings: Finding[];
  checks_performed: string[];
  input_type: string;
  created_at?: string;
}

export interface AuditSummary {
  id: number;
  created_at: string;
  input_type: string;
  language: string;
  checks_performed: string[];
  risk_score: number;
  summary: string;
  input_preview: string;
  finding_counts: Record<Severity, number>;
}

export interface StreamEvent {
  type: 'status' | 'finding' | 'complete' | 'error' | 'saved';
  data: any;
}
