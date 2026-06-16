import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuditRequest, AuditReport } from '../models/audit.models';

@Injectable({ providedIn: 'root' })
export class AuditService {
  private readonly apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  runAudit(request: AuditRequest): Observable<AuditReport> {
    return this.http.post<AuditReport>(`${this.apiUrl}/audit`, request);
  }

  checkHealth(): Observable<any> {
    return this.http.get(`${this.apiUrl}/health`);
  }
}
