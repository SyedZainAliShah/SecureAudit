import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditReport, Finding, Severity } from '../../models/audit.models';
import { FindingCardComponent } from '../finding-card/finding-card';

@Component({
  selector: 'app-audit-report',
  standalone: true,
  imports: [CommonModule, FindingCardComponent],
  templateUrl: './audit-report.html',
  styleUrl: './audit-report.scss'
})
export class AuditReportComponent {
  @Input() report!: AuditReport;
  @Output() reset = new EventEmitter<void>();

  activeFilter: Severity | 'all' = 'all';

  readonly severities: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];

  get filteredFindings(): Finding[] {
    if (this.activeFilter === 'all') return this.report.findings;
    return this.report.findings.filter(f => f.severity === this.activeFilter);
  }

  countBySeverity(s: Severity): number {
    return this.report.findings.filter(f => f.severity === s).length;
  }

  get riskLabel(): string {
    const s = this.report.risk_score;
    if (s >= 80) return 'Critical Risk';
    if (s >= 60) return 'High Risk';
    if (s >= 40) return 'Medium Risk';
    if (s >= 20) return 'Low Risk';
    return 'Minimal Risk';
  }

  get riskColor(): string {
    const s = this.report.risk_score;
    if (s >= 80) return '#ef4444';
    if (s >= 60) return '#f97316';
    if (s >= 40) return '#eab308';
    if (s >= 20) return '#3b82f6';
    return '#22c55e';
  }

  get circumference(): number { return 2 * Math.PI * 40; }

  get dashOffset(): number {
    return this.circumference * (1 - this.report.risk_score / 100);
  }

  copyMarkdown(): void {
    const lines: string[] = [
      `# SecureAudit Report`,
      ``,
      `**Risk Score:** ${this.report.risk_score}/100 — ${this.riskLabel}`,
      ``,
      `## Summary`,
      this.report.summary,
      ``,
      `## Findings (${this.report.findings.length})`,
      ``,
    ];

    for (const f of this.report.findings) {
      lines.push(`### [${f.severity.toUpperCase()}] ${f.title}`);
      lines.push(`**Category:** ${f.category}`);
      if (f.line_reference) lines.push(`**Location:** ${f.line_reference}`);
      lines.push(`**Issue:** ${f.description}`);
      lines.push(`**Fix:** ${f.recommendation}`);
      lines.push('');
    }

    navigator.clipboard.writeText(lines.join('\n'));
  }
}
