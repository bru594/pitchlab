"""
PitchLab - Leads API Routes
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User, Lead, LeadStatus
from app.services.lead_finder import find_leads
from app.services.credit_service import check_and_deduct

router = APIRouter()


class LeadSearchRequest(BaseModel):
    location: str
    niche: str
    max_results: int = 20
    no_website_only: bool = False
    poor_website_only: bool = False
    low_reviews_only: bool = False
    max_rating: Optional[float] = None


class LeadStatusUpdate(BaseModel):
    status: LeadStatus


@router.post("/search")
async def search_leads(
    req: LeadSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_and_deduct(user, db, cost=settings.CREDIT_COST_LEAD_SEARCH, reason="lead_search")

    filters = {
        "no_website_only":   req.no_website_only,
        "poor_website_only": req.poor_website_only,
        "low_reviews_only":  req.low_reviews_only,
    }
    if req.max_rating:
        filters["max_rating"] = req.max_rating

    found = await find_leads(
        location=req.location,
        niche=req.niche,
        filters=filters,
        max_results=req.max_results,
    )

    saved_leads = []
    for fl in found:
        existing = await db.execute(
            select(Lead).where(
                Lead.user_id == user.id,
                Lead.business_name == fl.business_name,
            )
        )
        if existing.scalar_one_or_none():
            continue

        lead = Lead(
            user_id=user.id,
            business_name=fl.business_name,
            website=fl.website,
            phone=fl.phone,
            address=fl.address,
            city=fl.city,
            state=fl.state,
            niche=fl.niche,
            rating=fl.rating,
            review_count=fl.review_count,
            has_website=fl.has_website,
            google_place_id=fl.google_place_id,
        )
        db.add(lead)
        saved_leads.append(lead)

    await db.flush()

    return {
        "found": len(found),
        "saved": len(saved_leads),
        "leads": [
            {
                "id": lead.id,
                "business_name": lead.business_name,
                "website": lead.website,
                "phone": lead.phone,
                "address": lead.address,
                "city": lead.city,
                "state": lead.state,
                "rating": lead.rating,
                "review_count": lead.review_count,
                "has_website": lead.has_website,
                "niche": lead.niche,
                "status": lead.status,
            }
            for lead in saved_leads
        ],
    }


@router.get("/")
async def list_leads(
    status: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    has_website: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Lead).where(Lead.user_id == user.id)

    if status:
        query = query.where(Lead.status == status)
    if niche:
        query = query.where(Lead.niche.ilike(f"%{niche}%"))
    if has_website is not None:
        query = query.where(Lead.has_website == has_website)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.options(
        selectinload(Lead.audit),
        selectinload(Lead.pitches),
    )
    query = query.order_by(Lead.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    leads = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "leads": [
            {
                "id": l.id,
                "business_name": l.business_name,
                "website": l.website,
                "phone": l.phone,
                "address": l.address,
                "city": l.city,
                "state": l.state,
                "rating": l.rating,
                "review_count": l.review_count,
                "has_website": l.has_website,
                "niche": l.niche,
                "status": l.status,
                "created_at": l.created_at.isoformat(),
                "has_audit": l.audit is not None,
                "has_pitch": len(l.pitches) > 0,
            }
            for l in leads
        ],
    }


@router.get("/{lead_id}")
async def get_lead(
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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lead not found")

    return {
        "id": lead.id,
        "business_name": lead.business_name,
        "website": lead.website,
        "phone": lead.phone,
        "address": lead.address,
        "city": lead.city,
        "state": lead.state,
        "rating": lead.rating,
        "review_count": lead.review_count,
        "has_website": lead.has_website,
        "niche": lead.niche,
        "status": lead.status,
        "created_at": lead.created_at.isoformat(),
        "audit": {
            "score":         lead.audit.score,
            "speed_score":   lead.audit.speed_score,
            "mobile_score":  lead.audit.mobile_score,
            "seo_score":     lead.audit.seo_score,
            "design_score":  lead.audit.design_score,
            "issues":        lead.audit.issues,
            "sales_summary": lead.audit.sales_summary,
        } if lead.audit else None,
        "pitches": [
            {
                "id": p.id,
                "cold_email": p.cold_email,
                "cold_call":  p.cold_call,
                "sms":        p.sms,
                "created_at": p.created_at.isoformat(),
            }
            for p in lead.pitches
        ],
    }


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    update: LeadStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id, Lead.user_id == user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = update.status
    await db.flush()
    return {"id": lead.id, "status": lead.status}


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    lead_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id, Lead.user_id == user.id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lead not found")

    await db.delete(lead)
