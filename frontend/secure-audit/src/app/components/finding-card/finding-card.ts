import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Finding } from '../../models/audit.models';

@Component({
  selector: 'app-finding-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './finding-card.html',
  styleUrl: './finding-card.scss'
})
export class FindingCardComponent implements OnChanges {
  @Input() finding!: Finding;
  @Input() forceExpanded = false;

  expanded = false;

  ngOnChanges(): void {
    if (this.forceExpanded) this.expanded = true;
  }

  toggle(): void {
    this.expanded = !this.expanded;
  }

  get severityLabel(): string {
    return this.finding.severity.toUpperCase();
  }

  get severityColor(): string {
    const map: Record<string, string> = {
      critical: '#ef4444', high: '#f97316', medium: '#eab308',
      low: '#3b82f6', info: '#6b7280'
    };
    return map[this.finding.severity] ?? '#6b7280';
  }
}
