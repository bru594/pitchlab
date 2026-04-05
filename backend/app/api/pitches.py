"""
PitchLab - Pitches API Routes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User, Lead, Audit, Pitch
from app.services.pitch_generator import generate_pitches
from app.services.credit_service import check_and_deduct

router = APIRouter()


@router.post("/{lead_id}/generate")
async def generate_pitch(
    lead_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lead)
        .options(
            selectinload(Lead.audit),
            selectinload(Lead.pitches),
        )
        .where(Lead.id == lead_id, Lead.user_id == user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if not lead.audit:
        raise HTTPException(status_code=400, detail="Run an audit first before generating pitches")

    await check_and_deduct(user, db, cost=settings.CREDIT_COST_PITCH_GENERATION, reason="pitch_generation")

    top_issues = [i["message"] for i in (lead.audit.issues or []) if i.get("severity") == "critical"]
    if not top_issues:
        top_issues = [i["message"] for i in (lead.audit.issues or [])[:3]]

    pitches = await generate_pitches(
        business_name=lead.business_name,
        niche=lead.niche or "local business",
        audit_summary=lead.audit.sales_summary or "",
        top_issues=top_issues,
    )

    pitch = Pitch(
        lead_id=lead_id,
        cold_email=f"Subject: {pitches.get('cold_email_subject', '')}\n\n{pitches.get('cold_email_body', '')}",
        cold_call=pitches.get("cold_call_script", ""),
        sms=pitches.get("sms", ""),
    )
    db.add(pitch)
    await db.flush()

    return {
        "pitch_id":           pitch.id,
        "cold_email_subject": pitches.get("cold_email_subject"),
        "cold_email_body":    pitches.get("cold_email_body"),
        "cold_call_script":   pitches.get("cold_call_script"),
        "sms":                pitches.get("sms"),
    }


@router.get("/{lead_id}")
async def list_pitches(
    lead_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lead)
        .options(selectinload(Lead.pitches))
        .where(Lead.id == lead_id, Lead.user_id == user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return [
        {
            "id": p.id,
            "cold_email": p.cold_email,
            "cold_call":  p.cold_call,
            "sms":        p.sms,
            "created_at": p.created_at.isoformat(),
        }
        for p in lead.pitches
    ]
