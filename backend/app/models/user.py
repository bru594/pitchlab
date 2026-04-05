"""
PitchLab - Database Models
Full schema: users, leads, audits, messages, credits, sequences.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def now_utc():
    return datetime.now(timezone.utc)


# ─── Enums ────────────────────────────────────────────────────────────────────

class PlanTier(str, enum.Enum):
    free = "free"
    pro = "pro"


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    replied = "replied"
    closed = "closed"
    ignored = "ignored"


class MessageStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    opened = "opened"
    replied = "replied"
    failed = "failed"


class SequenceStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    stopped = "stopped"  # stopped due to reply


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name       = Column(String(255))
    is_active       = Column(Boolean, default=True)
    plan            = Column(SAEnum(PlanTier), default=PlanTier.free)
    stripe_customer_id      = Column(String(255), nullable=True)
    stripe_subscription_id  = Column(String(255), nullable=True)
    created_at      = Column(DateTime(timezone=True), default=now_utc)
    updated_at      = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    credits   = relationship("CreditAccount", back_populates="user", uselist=False)
    leads     = relationship("Lead", back_populates="user")
    sequences = relationship("OutreachSequence", back_populates="user")


# ─── Credits ──────────────────────────────────────────────────────────────────

class CreditAccount(Base):
    __tablename__ = "credit_accounts"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), unique=True)
    balance         = Column(Integer, default=25)   # starts with free tier credits
    lifetime_used   = Column(Integer, default=0)
    last_reset_at   = Column(DateTime(timezone=True), default=now_utc)
    next_reset_at   = Column(DateTime(timezone=True), nullable=True)

    user         = relationship("User", back_populates="credits")
    transactions = relationship("CreditTransaction", back_populates="account")


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id          = Column(Integer, primary_key=True, index=True)
    account_id  = Column(Integer, ForeignKey("credit_accounts.id"))
    amount      = Column(Integer, nullable=False)  # negative = debit, positive = credit
    reason      = Column(String(255))              # e.g. "lead_search", "audit", "monthly_reset"
    created_at  = Column(DateTime(timezone=True), default=now_utc)

    account = relationship("CreditAccount", back_populates="transactions")


# ─── Lead ─────────────────────────────────────────────────────────────────────

class Lead(Base):
    __tablename__ = "leads"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), index=True)

    # Business info
    business_name   = Column(String(255), nullable=False)
    website         = Column(String(500), nullable=True)
    phone           = Column(String(50), nullable=True)
    address         = Column(String(500), nullable=True)
    city            = Column(String(100), nullable=True)
    state           = Column(String(50), nullable=True)
    niche           = Column(String(100), nullable=True)   # e.g. "plumber"
    google_place_id = Column(String(255), nullable=True)

    # Review data
    rating          = Column(Float, nullable=True)
    review_count    = Column(Integer, nullable=True)

    # Flags
    has_website     = Column(Boolean, default=True)
    status          = Column(SAEnum(LeadStatus), default=LeadStatus.new)

    created_at      = Column(DateTime(timezone=True), default=now_utc)
    updated_at      = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    user    = relationship("User", back_populates="leads")
    audit   = relationship("Audit", back_populates="lead", uselist=False)
    pitches = relationship("Pitch", back_populates="lead")


# ─── Audit ────────────────────────────────────────────────────────────────────

class Audit(Base):
    __tablename__ = "audits"

    id          = Column(Integer, primary_key=True, index=True)
    lead_id     = Column(Integer, ForeignKey("leads.id"), unique=True)

    url         = Column(String(500))
    score       = Column(Integer)   # 0-100 overall score

    # Sub-scores (0-100 each)
    speed_score     = Column(Integer, default=0)
    mobile_score    = Column(Integer, default=0)
    seo_score       = Column(Integer, default=0)
    design_score    = Column(Integer, default=0)

    # Detailed findings stored as JSON
    issues      = Column(JSON, default=list)   # list of issue strings
    raw_data    = Column(JSON, default=dict)   # raw scraped data

    # AI-generated sales summary
    sales_summary   = Column(Text, nullable=True)

    created_at  = Column(DateTime(timezone=True), default=now_utc)

    lead = relationship("Lead", back_populates="audit")


# ─── Pitch ────────────────────────────────────────────────────────────────────

class Pitch(Base):
    __tablename__ = "pitches"

    id          = Column(Integer, primary_key=True, index=True)
    lead_id     = Column(Integer, ForeignKey("leads.id"))

    cold_email  = Column(Text, nullable=True)
    cold_call   = Column(Text, nullable=True)
    sms         = Column(Text, nullable=True)

    created_at  = Column(DateTime(timezone=True), default=now_utc)

    lead = relationship("Lead", back_populates="pitches")


# ─── Outreach Sequence ────────────────────────────────────────────────────────

class OutreachSequence(Base):
    __tablename__ = "outreach_sequences"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"))
    lead_id     = Column(Integer, ForeignKey("leads.id"))
    name        = Column(String(255))
    status      = Column(SAEnum(SequenceStatus), default=SequenceStatus.active)

    current_step    = Column(Integer, default=0)
    total_steps     = Column(Integer, default=3)

    created_at  = Column(DateTime(timezone=True), default=now_utc)
    updated_at  = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    user     = relationship("User", back_populates="sequences")
    messages = relationship("Message", back_populates="sequence")


# ─── Message ──────────────────────────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id              = Column(Integer, primary_key=True, index=True)
    sequence_id     = Column(Integer, ForeignKey("outreach_sequences.id"), nullable=True)
    lead_id         = Column(Integer, ForeignKey("leads.id"))
    user_id         = Column(Integer, ForeignKey("users.id"))

    channel         = Column(String(20))   # "email" | "sms"
    subject         = Column(String(500), nullable=True)
    body            = Column(Text)
    step_number     = Column(Integer, default=1)

    status          = Column(SAEnum(MessageStatus), default=MessageStatus.pending)
    sent_at         = Column(DateTime(timezone=True), nullable=True)
    opened_at       = Column(DateTime(timezone=True), nullable=True)
    replied_at      = Column(DateTime(timezone=True), nullable=True)

    created_at      = Column(DateTime(timezone=True), default=now_utc)

    sequence = relationship("OutreachSequence", back_populates="messages")
