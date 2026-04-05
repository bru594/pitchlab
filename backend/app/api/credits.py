"""
PitchLab - Credits API Routes
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.credit_service import get_balance

router = APIRouter()


@router.get("/balance")
async def credit_balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's credit balance and transaction history."""
    return await get_balance(user, db)
