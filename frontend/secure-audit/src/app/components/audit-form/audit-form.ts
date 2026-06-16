import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuditRequest, CheckType, InputType } from '../../models/audit.models';

@Component({
  selector: 'app-audit-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './audit-form.html',
  styleUrl: './audit-form.scss'
})
export class AuditFormComponent {
  @Output() submitted = new EventEmitter<AuditRequest>();

  inputType: InputType = 'code';
  language = 'python';
  inputText = '';
  checks: Record<CheckType, boolean> = { owasp: true, gdpr: true };
  loading = false;

  languages = ['python', 'javascript', 'typescript', 'java', 'php', 'go', 'ruby', 'csharp', 'cpp', 'other'];

  get selectedChecks(): CheckType[] {
    return (Object.keys(this.checks) as CheckType[]).filter(k => this.checks[k]);
  }

  get isValid(): boolean {
    return this.inputText.trim().length > 10 && this.selectedChecks.length > 0;
  }

  get charCount(): number {
    return this.inputText.length;
  }

  onSubmit(): void {
    if (!this.isValid || this.loading) return;
    this.submitted.emit({
      input: this.inputText.trim(),
      input_type: this.inputType,
      language: this.language,
      checks: this.selectedChecks,
    });
  }

  loadExample(): void {
    this.inputType = 'code';
    this.language = 'python';
    this.inputText = `import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB = "users.db"

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    # Direct string interpolation — classic SQL injection
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    user = cursor.fetchone()

    if user:
        # Storing full user object in cookie without encryption
        response = jsonify({"status": "ok", "user": user})
        response.set_cookie("session_user", str(user), httponly=False)
        return response

    return jsonify({"error": "Invalid credentials", "db_path": DB}), 401

# Personal data endpoint — no auth required
@app.route("/users", methods=["GET"])
def get_all_users():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password, date_of_birth, health_status FROM users")
    return jsonify(cursor.fetchall())

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
`;
  }
}
