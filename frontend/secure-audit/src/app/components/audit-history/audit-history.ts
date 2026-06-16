import { Component, OnInit, Output, EventEmitter, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuditService } from '../../services/audit.service';
import { AuditSummary } from '../../models/audit.models';

@Component({
  selector: 'app-audit-history',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './audit-history.html',
  styleUrl: './audit-history.scss',
})
export class AuditHistoryComponent implements OnInit {
  @Output() loadAudit = new EventEmitter<number>();

  history: AuditSummary[] = [];
  loading = true;

  searchQuery = '';
  minRiskScore = 0;
  sortBy: 'date' | 'risk' = 'date';

  constructor(private auditService: AuditService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void { this.refresh(); }

  refresh(): void {
    this.loading = true;
    this.auditService.getHistory(50).subscribe({
      next: (h) => { this.history = h; this.loading = false; this.cdr.detectChanges(); },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  get filtered(): AuditSummary[] {
    let list = this.history;
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      list = list.filter(h =>
        h.input_preview.toLowerCase().includes(q) ||
        h.summary.toLowerCase().includes(q) ||
        h.language?.toLowerCase().includes(q)
      );
    }
    if (this.minRiskScore > 0) {
      list = list.filter(h => h.risk_score >= this.minRiskScore);
    }
    if (this.sortBy === 'risk') {
      list = [...list].sort((a, b) => b.risk_score - a.risk_score);
    }
    return list;
  }

  delete(id: number, event: MouseEvent): void {
    event.stopPropagation();
    this.auditService.deleteAudit(id).subscribe(() => {
      this.history = this.history.filter(h => h.id !== id);
      this.cdr.detectChanges();
    });
  }

  riskColor(score: number): string {
    if (score >= 85) return '#ef4444';
    if (score >= 60) return '#f97316';
    if (score >= 35) return '#eab308';
    if (score >= 10) return '#3b82f6';
    return '#22c55e';
  }

  formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleString('en-GB', {
      day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
    });
  }

  totalFindings(counts: Record<string, number>): number {
    return Object.values(counts).reduce((a, b) => a + b, 0);
  }
}
