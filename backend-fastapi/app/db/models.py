"""SQLAlchemy models — a 1:1 translation of the Django ORM models.

Column lengths, defaults, orderings and index names match ``schema.dbml`` so
a ``pg_dump`` from the Django database can be imported without reshaping.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigPK, TimestampMixin, utcnow

# ---------------------------------------------------------------------------
# Choices (mirrored from the Django TextChoices classes)
# ---------------------------------------------------------------------------
USER_ROLES = ("student", "premium", "admin")

EXPENSE_CATEGORIES = ("food", "travel", "shopping", "education", "entertainment", "misc")
PAYMENT_METHODS = ("cash", "upi", "card", "bank")
INCOME_SOURCES = ("pocket_money", "scholarship", "freelance", "part_time", "gift", "other")
GOAL_PRIORITIES = ("low", "medium", "high")

NOTIFICATION_TYPES = ("budget", "savings", "goal", "report", "system")
REPORT_TYPES = ("monthly", "expense", "income", "savings")
REPORT_FORMATS = ("pdf", "excel")
CHAT_ROLES = ("user", "assistant", "system")

CATEGORY_LABELS = {
    "food": "Food",
    "travel": "Travel",
    "shopping": "Shopping",
    "education": "Education",
    "entertainment": "Entertainment",
    "misc": "Miscellaneous",
}

SOURCE_LABELS = {
    "pocket_money": "Pocket money",
    "scholarship": "Scholarship",
    "freelance": "Freelance",
    "part_time": "Part-time job",
    "gift": "Gift",
    "other": "Other",
}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(128), nullable=False)
    first_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    last_name: Mapped[str] = mapped_column(String(150), nullable=False, default="")
    role: Mapped[str] = mapped_column(String(10), nullable=False, default="student", index=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    date_joined: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    profile: Mapped["Profile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="joined"
    )
    expenses: Mapped[list["Expense"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    incomes: Mapped[list["Income"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    savings_goals: Mapped[list["SavingsGoal"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_authenticated(self) -> bool:  # Django parity for convenience
        return True


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="profiles_user_id_fk"),
        unique=True,
        nullable=False,
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    avatar_url: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    monthly_income: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    financial_preferences: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )

    user: Mapped["User"] = relationship(back_populates="profile")


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expense_user_date", "user_id", "date"),
        Index("ix_expense_user_category", "user_id", "category"),
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="expenses_user_id_fk"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(15), nullable=False, default="misc")
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(12), nullable=False, default="cash")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    user: Mapped["User"] = relationship(back_populates="expenses")


class Income(TimestampMixin, Base):
    __tablename__ = "incomes"
    __table_args__ = (
        Index("ix_income_user_date", "user_id", "date"),
        Index("ix_income_user_source", "user_id", "source_type"),
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="incomes_user_id_fk"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pocket_money"
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    user: Mapped["User"] = relationship(back_populates="incomes")


class Budget(TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "month", "category", name="uq_budget_user_month_category"),
        Index("ix_budget_user_month", "user_id", "month"),
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="budgets_user_id_fk"), nullable=False
    )
    month: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(15), nullable=False, default="misc")
    limit_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )

    user: Mapped["User"] = relationship(back_populates="budgets")


class SavingsGoal(TimestampMixin, Base):
    __tablename__ = "savings_goals"
    __table_args__ = (
        Index("ix_goal_user_status", "user_id", "is_completed"),
        Index("ix_goal_user_deadline", "user_id", "target_date"),
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="savings_goals_user_id_fk"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    user: Mapped["User"] = relationship(back_populates="savings_goals")

    # Django's model.save() recomputes this on every write.
    def sync_completion(self) -> bool:
        self.is_completed = Decimal(self.current_amount or 0) >= Decimal(self.target_amount or 0)
        return self.is_completed


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notification_user_read", "user_id", "is_read"),
        Index("ix_notification_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="notifications_user_id_fk"),
        nullable=False,
    )
    notification_type: Mapped[str] = mapped_column(String(10), nullable=False, default="system")
    title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    user: Mapped["User"] = relationship(back_populates="notifications")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_report_user_month", "user_id", "month"),)

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="reports_user_id_fk"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(10), nullable=False, default="monthly")
    month: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False, default="pdf")
    file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="reports")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="chat_messages_user_id_fk"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(15), nullable=False, default="user")
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    action_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    user: Mapped["User"] = relationship(back_populates="chat_messages")
