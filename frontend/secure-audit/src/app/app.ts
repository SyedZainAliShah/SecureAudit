import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditFormComponent } from './components/audit-form/audit-form';
import { AuditReportComponent } from './components/audit-report/audit-report';
import { AuditService } from './services/audit.service';
import { AuditRequest, AuditReport } from './models/audit.models';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, AuditFormComponent, AuditReportComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  report: AuditReport | null = null;
  loading = false;
  error: string | null = null;

  constructor(private auditService: AuditService) {}

  onAuditSubmit(req: AuditRequest): void {
    this.loading = true;
    this.error = null;
    this.report = null;

    this.auditService.runAudit(req).subscribe({
      next: (r) => {
        this.report = r;
        this.loading = false;
      },
      error: (e) => {
        this.error = e?.error?.detail ?? 'Audit failed. Is Ollama running?';
        this.loading = false;
      },
    });
  }

  reset(): void {
    this.report = null;
    this.error = null;
  }
}
