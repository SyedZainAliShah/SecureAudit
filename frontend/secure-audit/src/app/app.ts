import { Component, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditFormComponent } from './components/audit-form/audit-form';
import { AuditReportComponent } from './components/audit-report/audit-report';
import { AuditHistoryComponent } from './components/audit-history/audit-history';
import { AuditChartComponent } from './components/audit-chart/audit-chart';
import { AuditService } from './services/audit.service';
import { AuditRequest, AuditReport, AuditSummary, Finding } from './models/audit.models';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, AuditFormComponent, AuditReportComponent, AuditHistoryComponent, AuditChartComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  @ViewChild(AuditHistoryComponent) historyRef?: AuditHistoryComponent;

  report: AuditReport | null = null;
  lastRequest: AuditRequest | null = null;
  prefillRequest: AuditRequest | null = null;
  loading = false;
  error: string | null = null;
  activeTab: 'audit' | 'history' | 'analytics' = 'audit';

  // Streaming state
  streamProgress = 0;
  streamMessage = '';
  streamFindings: Finding[] = [];
  streaming = false;

  history: AuditSummary[] = [];

  constructor(private auditService: AuditService, private cdr: ChangeDetectorRef) {}

  onRerun(req: AuditRequest): void {
    this.prefillRequest = req;
    this.report = null;
    this.error = null;
    this.cdr.detectChanges();
  }

  onAuditSubmit(req: AuditRequest): void {
    this.lastRequest = req;
    this.prefillRequest = null;
    this.loading = true;
    this.streaming = true;
    this.error = null;
    this.report = null;
    this.streamFindings = [];
    this.streamProgress = 0;
    this.streamMessage = 'Starting audit...';
    this.cdr.detectChanges();

    const stream$ = this.auditService.streamAudit(req);

    stream$.subscribe({
      next: (event) => {
        switch (event.type) {
          case 'status':
            this.streamProgress = event.data.progress ?? this.streamProgress;
            this.streamMessage = event.data.message ?? this.streamMessage;
            break;
          case 'finding':
            this.streamFindings = [...this.streamFindings, event.data.finding];
            break;
          case 'complete':
            this.report = event.data.report;
            this.loading = false;
            this.streaming = false;
            this.streamProgress = 100;
            // Refresh history and analytics
            this.loadHistory();
            break;
          case 'error':
            this.error = event.data.message ?? 'Audit failed.';
            this.loading = false;
            this.streaming = false;
            break;
        }
        this.cdr.detectChanges();
      },
      error: (e) => {
        this.error = 'Connection failed. Is the backend running?';
        this.loading = false;
        this.streaming = false;
        this.cdr.detectChanges();
      },
      complete: () => {
        this.loading = false;
        this.streaming = false;
        this.cdr.detectChanges();
      }
    });
  }

  loadHistory(): void {
    this.auditService.getHistory().subscribe({
      next: (h) => { this.history = h; this.cdr.detectChanges(); },
    });
  }

  loadAuditFromHistory(id: number): void {
    this.activeTab = 'audit';
    this.loading = true;
    this.cdr.detectChanges();
    this.auditService.getAudit(id).subscribe({
      next: (r) => { this.report = r; this.loading = false; this.cdr.detectChanges(); },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  reset(): void {
    this.report = null;
    this.lastRequest = null;
    this.prefillRequest = null;
    this.error = null;
    this.streamFindings = [];
    this.streamProgress = 0;
    this.cdr.detectChanges();
  }

  switchTab(tab: 'audit' | 'history' | 'analytics'): void {
    this.activeTab = tab;
    if (tab === 'history' || tab === 'analytics') this.loadHistory();
    this.cdr.detectChanges();
  }
}