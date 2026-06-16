from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    input_type: Mapped[str] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(50), nullable=True)
    checks_performed: Mapped[list] = mapped_column(JSON)
    risk_score: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    findings: Mapped[list] = mapped_column(JSON)   # store as JSON array
    input_preview: Mapped[str] = mapped_column(Text)  # first 200 chars of input
