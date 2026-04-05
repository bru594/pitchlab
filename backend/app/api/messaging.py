"""
PitchLab - Messaging API Routes
Send emails/SMS, manage outreach sequences.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import (
    User, Lead, Message, OutreachSequence,
    MessageStatus, SequenceStatus
)
from app.services.messaging_service import send_email, send_sms, mark_message_sent
from app.services.credit_service import check_and_deduct

router = APIRouter()


class SendMessageRequest(BaseModel):
    lead_id: int
    channel: str        # "email" or "sms"
    subject: Optional[str] = None
    body: str
    to_address: Optional[str] = None   # email address or phone number


class CreateSequenceRequest(BaseModel):
    lead_id: int
    name: str
    steps: List[dict]   # [{"channel": "email", "subject": "...", "body": "...", "delay_days": 2}]


@router.post("/send")
async def send_message(
    req: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a single email or SMS to a lead. Costs 1 credit."""
    result = await db.execute(
        select(Lead).where(Lead.id == req.lead_id, Lead.user_id == user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Deduct credits
    await check_and_deduct(user, db, cost=settings.CREDIT_COST_MESSAGE_SEND, reason="message_send")

    # Create message record
    msg = Message(
        lead_id=req.lead_id,
        user_id=user.id,
        channel=req.channel,
        subject=req.subject,
        body=req.body,
        status=MessageStatus.pending,
    )
    db.add(msg)
    await db.flush()

    # Dispatch
    success = False
    to_addr = req.to_address

    if req.channel == "email":
        if not to_addr and lead.website:
            domain = lead.website.replace("https://", "").replace("http://", "").split("/")[0]
            to_addr = f"contact@{domain}"
        if to_addr:
            success = await send_email(to_addr, req.subject or "Quick question", req.body)
    elif req.channel == "sms":
        to_addr = to_addr or lead.phone
        if to_addr:
            success = await send_sms(to_addr, req.body)

    if success:
        await mark_message_sent(msg, db)
        # Update lead status
        from app.models.user import LeadStatus
        if lead.status == LeadStatus.new:
            lead.status = LeadStatus.contacted

    return {
        "message_id": msg.id,
        "status": msg.status,
        "sent": success,
    }


@router.post("/sequences")
async def create_sequence(
    req: CreateSequenceRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a multi-step outreach sequence for a lead."""
    result = await db.execute(
        select(Lead).where(Lead.id == req.lead_id, Lead.user_id == user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if len(req.steps) < 1 or len(req.steps) > 5:
        raise HTTPException(status_code=400, detail="Sequences must have 1-5 steps")

    # Create sequence
    seq = OutreachSequence(
        user_id=user.id,
        lead_id=req.lead_id,
        name=req.name,
        total_steps=len(req.steps),
        status=SequenceStatus.active,
    )
    db.add(seq)
    await db.flush()

    # Create message records for each step
    for i, step in enumerate(req.steps):
        msg = Message(
            sequence_id=seq.id,
            lead_id=req.lead_id,
            user_id=user.id,
            channel=step.get("channel", "email"),
            subject=step.get("subject"),
            body=step.get("body", ""),
            step_number=i + 1,
            status=MessageStatus.pending,
        )
        db.add(msg)

    await db.flush()
    return {"sequence_id": seq.id, "steps": len(req.steps), "status": seq.status}


@router.get("/sequences")
async def list_sequences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all outreach sequences for the user."""
    result = await db.execute(
        select(OutreachSequence)
        .where(OutreachSequence.user_id == user.id)
        .order_by(OutreachSequence.created_at.desc())
    )
    seqs = result.scalars().all()

    return [
        {
            "id": s.id,
            "lead_id": s.lead_id,
            "name": s.name,
            "status": s.status,
            "current_step": s.current_step,
            "total_steps": s.total_steps,
            "created_at": s.created_at.isoformat(),
            "message_count": len(s.messages),
            "sent_count": sum(1 for m in s.messages if m.status in [MessageStatus.sent, MessageStatus.opened, MessageStatus.replied]),
            "has_reply": any(m.status == MessageStatus.replied for m in s.messages),
        }
        for s in seqs
    ]


@router.get("/history")
async def message_history(
    lead_id: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get message history, optionally filtered by lead."""
    query = select(Message).where(Message.user_id == user.id)
    if lead_id:
        query = query.where(Message.lead_id == lead_id)
    query = query.order_by(Message.created_at.desc()).limit(100)

    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        {
            "id": m.id,
            "lead_id": m.lead_id,
            "channel": m.channel,
            "subject": m.subject,
            "body": m.body[:200] + "..." if m.body and len(m.body) > 200 else m.body,
            "status": m.status,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "opened_at": m.opened_at.isoformat() if m.opened_at else None,
            "replied_at": m.replied_at.isoformat() if m.replied_at else None,
        }
        for m in messages
    ]


# Track opens via pixel (optional feature)
@router.get("/track/{message_id}/open")
async def track_open(message_id: int, db: AsyncSession = Depends(get_db)):
    """Tracking pixel endpoint — marks message as opened."""
    from app.services.messaging_service import mark_message_opened
    await mark_message_opened(message_id, db)
    # Return 1x1 transparent GIF
    from fastapi.responses import Response
    pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    return Response(content=pixel, media_type="image/gif")


# Optional import for type hints in list_sequences
from typing import Optional
