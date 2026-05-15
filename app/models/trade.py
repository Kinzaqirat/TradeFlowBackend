"""SQLAlchemy Trade model with all trading fields."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import String, DateTime, Numeric, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Trade details
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(5), nullable=False)  # LONG | SHORT
    entry_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    exit_price: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)

    # Calculated fields (stored for query performance)
    pnl: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    pnl_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    result: Mapped[str] = mapped_column(String(10), nullable=False)  # WIN|LOSS|BREAKEVEN

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="trades")
