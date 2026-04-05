"""
PitchLab - Audits API Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User, Lead, Audit
from app.services.audit_engine import audit_website, mock_no_website_audit
from app.services.credit_service import check_and_deduct

router = APIRouter()


@router.post("/{lead_id}/run")
async def run_audit(
    lead_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a full website audit on a lead. Costs credits."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id, Lead.user_id == user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Deduct credits
    await check_and_deduct(user, db, cost=settings.CREDIT_COST_AUDIT, reason="audit")

    # Run audit
    if not lead.website:
        audit_data = mock_no_website_audit(lead.business_name)
    else:
        audit_data = await audit_website(lead.website, lead.business_name)

    # Save or update audit record
    existing = await db.execute(select(Audit).where(Audit.lead_id == lead_id))
    audit = existing.scalar_one_or_none()

    if audit:
        audit.score         = audit_data["overall_score"]
        audit.speed_score   = audit_data["speed_score"]
        audit.mobile_score  = audit_data["mobile_score"]
        audit.seo_score     = audit_data["seo_score"]
        audit.design_score  = audit_data["design_score"]
        audit.issues        = audit_data["all_issues"]
        audit.raw_data      = audit_data["raw_data"]
        audit.sales_summary = audit_data["sales_summary"]
        audit.url           = audit_data.get("url") or lead.website
    else:
        audit = Audit(
            lead_id=lead_id,
            url=audit_data.get("url") or lead.website,
            score=audit_data["overall_score"],
            speed_score=audit_data["speed_score"],
            mobile_score=audit_data["mobile_score"],
            seo_score=audit_data["seo_score"],
            design_score=audit_data["design_score"],
            issues=audit_data["all_issues"],
            raw_data=audit_data["raw_data"],
            sales_summary=audit_data["sales_summary"],
        )
        db.add(audit)

    await db.flush()
    return {"audit_id": audit.id, **audit_data}


@router.get("/{lead_id}")
async def get_audit(
    lead_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the stored audit for a lead."""
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id, Lead.user_id == user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if not lead.audit:
        raise HTTPException(status_code=404, detail="No audit found — run one first")

    a = lead.audit
    return {
        "audit_id":      a.id,
        "url":           a.url,
        "score":         a.score,
        "speed_score":   a.speed_score,
        "mobile_score":  a.mobile_score,
        "seo_score":     a.seo_score,
        "design_score":  a.design_score,
        "issues":        a.issues,
        "sales_summary": a.sales_summary,
        "created_at":    a.created_at.isoformat(),
    }
