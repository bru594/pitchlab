"""
PitchLab - Promo Code API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.promo_service import redeem_promo

router = APIRouter()


class RedeemRequest(BaseModel):
    code: str


@router.post("/redeem")
async def redeem_code(
    req: RedeemRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await redeem_promo(req.code, user, db)
