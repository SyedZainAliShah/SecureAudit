import { Component, EventEmitter, Input, Output, OnChanges, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuditRequest, CheckType, InputType } from '../../models/audit.models';
import { AuditService } from '../../services/audit.service';

@Component({
  selector: 'app-audit-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './audit-form.html',
  styleUrl: './audit-form.scss'
})
export class AuditFormComponent implements OnChanges {
  @Input() prefill: AuditRequest | null = null;
  @Output() submitted = new EventEmitter<AuditRequest>();

  inputType: InputType = 'code';
  language = 'python';
  inputText = '';
  checks: Record<CheckType, boolean> = { owasp: true, gdpr: true, secrets: true, pci: false, hipaa: false };
  loading = false;

  // GitHub
  githubUrl = '';
  githubFetching = false;
  githubInfo: { repo: string; files: string[]; truncated: boolean } | null = null;
  githubError = '';

  // File upload
  isDragging = false;
  uploadedFileName = '';

  languages = ['python', 'javascript', 'typescript', 'java', 'php', 'go', 'ruby', 'csharp', 'cpp', 'other'];

  constructor(private auditService: AuditService) {}

  ngOnChanges(): void {
    if (this.prefill) {
      this.inputText = this.prefill.input;
      this.inputType = this.prefill.input_type as InputType;
      this.language = this.prefill.language;
      const checks: Record<CheckType, boolean> = { owasp: false, gdpr: false, secrets: false, pci: false, hipaa: false };
      for (const c of this.prefill.checks) checks[c] = true;
      this.checks = checks;
      this.githubInfo = null;
      this.uploadedFileName = '';
    }
  }

  get selectedChecks(): CheckType[] {
    return (Object.keys(this.checks) as CheckType[]).filter(k => this.checks[k]);
  }

  get isValid(): boolean {
    if (this.inputType === 'github') return this.inputText.trim().length > 10 && this.selectedChecks.length > 0;
    return this.inputText.trim().length > 10 && this.selectedChecks.length > 0;
  }

  get charCount(): number { return this.inputText.length; }

  setInputType(t: InputType): void {
    this.inputType = t;
    this.githubInfo = null;
    this.githubError = '';
    this.uploadedFileName = '';
  }

  // ── GitHub fetch ──────────────────────────────────────────────────────────

  fetchGithub(): void {
    if (!this.githubUrl.trim()) return;
    this.githubFetching = true;
    this.githubError = '';
    this.githubInfo = null;
    this.inputText = '';

    this.auditService.fetchGithub(this.githubUrl.trim()).subscribe({
      next: (res) => {
        this.inputText = res.content;
        this.language = res.language;
        this.githubInfo = { repo: res.repo, files: res.files_fetched, truncated: res.truncated };
        this.githubFetching = false;
      },
      error: (err) => {
        this.githubError = err.error?.detail ?? 'Failed to fetch repository.';
        this.githubFetching = false;
      }
    });
  }

  // ── File upload ───────────────────────────────────────────────────────────

  @HostListener('dragover', ['$event'])
  onDragOver(e: DragEvent): void { e.preventDefault(); }

  onDropzoneDragOver(e: DragEvent): void { e.preventDefault(); this.isDragging = true; }
  onDropzoneDragLeave(): void { this.isDragging = false; }

  onDropzoneDrop(e: DragEvent): void {
    e.preventDefault();
    this.isDragging = false;
    const file = e.dataTransfer?.files?.[0];
    if (file) this.readFile(file);
  }

  onFileSelected(e: Event): void {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) this.readFile(file);
  }

  private readFile(file: File): void {
    const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
    const extLangMap: Record<string, string> = {
      py: 'python', js: 'javascript', ts: 'typescript', java: 'java',
      go: 'go', rb: 'ruby', php: 'php', cs: 'csharp', cpp: 'cpp',
      jsx: 'javascript', tsx: 'typescript', rs: 'other',
    };
    if (extLangMap[ext]) this.language = extLangMap[ext];

    const reader = new FileReader();
    reader.onload = (ev) => {
      this.inputText = (ev.target?.result as string ?? '').slice(0, 8000);
      this.uploadedFileName = file.name;
      this.inputType = 'code';
    };
    reader.readAsText(file);
  }

  // ── Submit ────────────────────────────────────────────────────────────────

  onSubmit(): void {
    if (!this.isValid || this.loading) return;
    this.submitted.emit({
      input: this.inputText.trim(),
      input_type: this.inputType === 'github' ? 'code' : this.inputType,
      language: this.language,
      checks: this.selectedChecks,
    });
  }

  loadExample(): void {
    this.inputType = 'code';
    this.language = 'python';
    this.githubInfo = null;
    this.uploadedFileName = '';
    this.inputText = `import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PASSWORD = "admin123"  # Hardcoded credential

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    user = cursor.fetchone()
    if user:
        response = jsonify({"status": "ok", "user": user})
        response.set_cookie("session_user", str(user), httponly=False)
        return response
    return jsonify({"error": "Invalid credentials", "db_path": DB_PASSWORD}), 401

@app.route("/users")
def get_all_users():
    # No auth, returns PII including health data
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password, date_of_birth, health_status FROM users")
    return jsonify(cursor.fetchall())

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")`;
  }
}
