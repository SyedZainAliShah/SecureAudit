import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Finding } from '../../models/audit.models';

@Component({
  selector: 'app-finding-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './finding-card.html',
  styleUrl: './finding-card.scss'
})
export class FindingCardComponent {
  @Input() finding!: Finding;
  expanded = false;

  get severityLabel(): string {
    return this.finding.severity.toUpperCase();
  }

  get severityIcon(): string {
    const icons: Record<string, string> = {
      critical: '🔴', high: '🟠', medium: '🟡', low: '🔵', info: '⚪'
    };
    return icons[this.finding.severity] ?? '⚪';
  }
}
