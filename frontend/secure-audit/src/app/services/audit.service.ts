import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import { AuditRequest, AuditReport, AuditSummary, StreamEvent, GitHubFetchResponse } from '../models/audit.models';

@Injectable({ providedIn: 'root' })
export class AuditService {
  private readonly apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  runAudit(request: AuditRequest): Observable<AuditReport> {
    return this.http.post<AuditReport>(`${this.apiUrl}/audit`, request);
  }

  /** Streaming audit via SSE. Returns a Subject that emits parsed StreamEvents. */
  streamAudit(request: AuditRequest): Subject<StreamEvent> {
    const subject = new Subject<StreamEvent>();

    fetch(`${this.apiUrl}/audit/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    }).then(async (response) => {
      if (!response.ok) {
        subject.error(new Error(`HTTP ${response.status}`));
        return;
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) { subject.complete(); break; }

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() ?? '';

        for (const part of parts) {
          if (!part.trim()) continue;
          let eventType = 'message';
          let dataLine = '';

          for (const line of part.split('\n')) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim();
            if (line.startsWith('data: '))  dataLine  = line.slice(6).trim();
          }

          if (dataLine) {
            try {
              subject.next({ type: eventType as any, data: JSON.parse(dataLine) });
            } catch { /* skip malformed */ }
          }
        }
      }
    }).catch(err => subject.error(err));

    return subject;
  }

  getHistory(limit = 20): Observable<AuditSummary[]> {
    return this.http.get<AuditSummary[]>(`${this.apiUrl}/audits?limit=${limit}`);
  }

  getAudit(id: number): Observable<AuditReport> {
    return this.http.get<AuditReport>(`${this.apiUrl}/audits/${id}`);
  }

  deleteAudit(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/audits/${id}`);
  }

  fetchGithub(url: string): Observable<GitHubFetchResponse> {
    return this.http.post<GitHubFetchResponse>(`${this.apiUrl}/github-fetch`, { url });
  }

  checkHealth(): Observable<any> {
    return this.http.get(`${this.apiUrl}/health`);
  }
}
