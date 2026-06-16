import {
  Component, Input, OnChanges, ViewChild,
  ElementRef, AfterViewInit, ChangeDetectorRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditSummary } from '../../models/audit.models';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

const SEV_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high:     '#ea580c',
  medium:   '#ca8a04',
  low:      '#2563eb',
  info:     '#6b7280',
};

@Component({
  selector: 'app-audit-chart',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './audit-chart.html',
  styleUrl: './audit-chart.scss',
})
export class AuditChartComponent implements OnChanges, AfterViewInit {
  @Input() history: AuditSummary[] = [];
  @ViewChild('barCanvas')    barCanvas!:    ElementRef<HTMLCanvasElement>;
  @ViewChild('lineCanvas')   lineCanvas!:   ElementRef<HTMLCanvasElement>;
  @ViewChild('donutCanvas')  donutCanvas!:  ElementRef<HTMLCanvasElement>;

  private barChart:   Chart | null = null;
  private lineChart:  Chart | null = null;
  private donutChart: Chart | null = null;
  private ready = false;

  constructor(private cdr: ChangeDetectorRef) {}

  ngAfterViewInit(): void { this.ready = true; this.buildCharts(); }
  ngOnChanges(): void     { if (this.ready) this.buildCharts(); }

  private buildCharts(): void {
    if (!this.history.length) return;
    this.buildBarChart();
    this.buildLineChart();
    this.buildDonutChart();
    this.cdr.detectChanges();
  }

  private chartDefaults() {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
    };
  }

  private buildBarChart(): void {
    const totals = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const h of this.history)
      for (const [k, v] of Object.entries(h.finding_counts))
        (totals as any)[k] = ((totals as any)[k] ?? 0) + v;

    if (this.barChart) this.barChart.destroy();
    this.barChart = new Chart(this.barCanvas.nativeElement, {
      type: 'bar',
      data: {
        labels: ['Critical', 'High', 'Medium', 'Low', 'Info'],
        datasets: [{
          data: [totals.critical, totals.high, totals.medium, totals.low, totals.info],
          backgroundColor: [
            'rgba(220,38,38,0.12)', 'rgba(234,88,12,0.12)',
            'rgba(202,138,4,0.12)', 'rgba(37,99,235,0.12)', 'rgba(107,114,128,0.1)',
          ],
          borderColor: ['#dc2626','#ea580c','#ca8a04','#2563eb','#9ca3af'],
          borderWidth: 2,
          borderRadius: 6,
          borderSkipped: false,
        }],
      },
      options: {
        ...this.chartDefaults(),
        scales: {
          x: {
            grid: { color: '#f3f4f6' },
            ticks: { color: '#6b7280', font: { size: 11 } },
            border: { display: false },
          },
          y: {
            grid: { color: '#f3f4f6' },
            ticks: { color: '#6b7280', stepSize: 1, font: { size: 11 } },
            border: { display: false },
            beginAtZero: true,
          },
        },
      },
    });
  }

  private buildLineChart(): void {
    const recent = [...this.history].reverse().slice(-10);
    const labels = recent.map((h, i) => `#${i + 1}`);
    const scores = recent.map(h => h.risk_score);

    if (this.lineChart) this.lineChart.destroy();
    this.lineChart = new Chart(this.lineCanvas.nativeElement, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Risk Score',
          data: scores,
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37,99,235,0.06)',
          fill: true,
          tension: 0.4,
          pointRadius: 5,
          pointHoverRadius: 7,
          pointBackgroundColor: scores.map(s =>
            s >= 80 ? '#dc2626' : s >= 60 ? '#ea580c' : s >= 40 ? '#ca8a04' : '#2563eb'
          ),
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
        }],
      },
      options: {
        ...this.chartDefaults(),
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#fff',
            titleColor: '#111827',
            bodyColor: '#374151',
            borderColor: '#e5e7eb',
            borderWidth: 1,
            padding: 10,
            callbacks: { label: (ctx) => ` Risk score: ${ctx.parsed.y}` },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#6b7280', font: { size: 11 } },
            border: { display: false },
          },
          y: {
            grid: { color: '#f3f4f6' },
            ticks: { color: '#6b7280', font: { size: 11 } },
            border: { display: false },
            min: 0, max: 100,
          },
        },
      },
    });
  }

  private buildDonutChart(): void {
    const totals = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const h of this.history)
      for (const [k, v] of Object.entries(h.finding_counts))
        (totals as any)[k] = ((totals as any)[k] ?? 0) + v;

    const entries = Object.entries(totals).filter(([, v]) => v > 0);
    if (!entries.length) return;

    if (this.donutChart) this.donutChart.destroy();
    this.donutChart = new Chart(this.donutCanvas.nativeElement, {
      type: 'doughnut',
      data: {
        labels: entries.map(([k]) => k.charAt(0).toUpperCase() + k.slice(1)),
        datasets: [{
          data: entries.map(([, v]) => v),
          backgroundColor: entries.map(([k]) => SEV_COLORS[k] + '22'),
          borderColor: entries.map(([k]) => SEV_COLORS[k]),
          borderWidth: 2,
          hoverOffset: 6,
        }],
      },
      options: {
        ...this.chartDefaults(),
        cutout: '68%',
        plugins: {
          legend: {
            display: true,
            position: 'right',
            labels: { color: '#374151', font: { size: 11 }, padding: 12, boxWidth: 10, boxHeight: 10 },
          },
          tooltip: {
            backgroundColor: '#fff',
            titleColor: '#111827',
            bodyColor: '#374151',
            borderColor: '#e5e7eb',
            borderWidth: 1,
            padding: 10,
          },
        },
      },
    });
  }

  get avgRisk(): number {
    if (!this.history.length) return 0;
    return Math.round(this.history.reduce((s, h) => s + h.risk_score, 0) / this.history.length);
  }

  get avgRiskColor(): string {
    const r = this.avgRisk;
    return r >= 80 ? '#dc2626' : r >= 60 ? '#ea580c' : r >= 40 ? '#ca8a04' : '#16a34a';
  }

  get totalFindings(): number {
    return this.history.reduce((s, h) =>
      s + Object.values(h.finding_counts).reduce((a, b) => a + b, 0), 0);
  }

  get mostCommonSeverity(): string {
    const totals: Record<string, number> = {};
    for (const h of this.history)
      for (const [k, v] of Object.entries(h.finding_counts))
        totals[k] = (totals[k] ?? 0) + v;
    return Object.entries(totals).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '—';
  }

  get criticalCount(): number {
    return this.history.reduce((s, h) => s + (h.finding_counts['critical'] ?? 0), 0);
  }

  get highCount(): number {
    return this.history.reduce((s, h) => s + (h.finding_counts['high'] ?? 0), 0);
  }

  get riskTrend(): 'up' | 'down' | 'flat' {
    if (this.history.length < 2) return 'flat';
    const recent = [...this.history].reverse();
    const diff = recent[recent.length - 1].risk_score - recent[0].risk_score;
    return diff > 5 ? 'up' : diff < -5 ? 'down' : 'flat';
  }
}
