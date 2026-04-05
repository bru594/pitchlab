"""
PitchLab - Promo Code Service
"""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.user import User, CreditAccount
from app.services.credit_service import add_credits

# ── Hardcoded promo codes ──────────────────────────────────────────────────
# Format: "CODE": {"credits": 100, "max_uses": 50, "description": "..."}
# Set max_uses to None for unlimited
# Set credits to 99999 for developer/unlimited access

PROMO_CODES = {
    "DEVMASTER": {"credits": 99999, "max_uses": None, "description": "Developer unlimited access"},
    "LAUNCH50":  {"credits": 50,    "max_uses": 100,  "description": "Launch promo - 50 credits"},
    "GOGGIN25":  {"credits": 25,    "max_uses": None,  "description": "Goggin Digital promo"},
    "BETA100":   {"credits": 100,   "max_uses": 50,   "description": "Beta tester bonus"},
}

# Track uses in memory (resets on server restart)
# For production, store this in the database
_code_uses: dict = {}


async def redeem_promo(code: str, user: User, db: AsyncSession) -> dict:
    """Redeem a promo code for credits."""
    code_upper = code.strip().upper()

    if code_upper not in PROMO_CODES:
        raise HTTPException(status_code=400, detail="Invalid promo code")

    promo = PROMO_CODES[code_upper]

    # Check max uses
    uses = _code_uses.get(code_upper, 0)
    if promo["max_uses"] is not None and uses >= promo["max_uses"]:
        raise HTTPException(status_code=400, detail="This promo code has expired")

    # Add credits
    credits = promo["credits"]
    await add_credits(user, db, amount=credits, reason=f"promo_{code_upper}")

    # Track use
    _code_uses[code_upper] = uses + 1

    return {
        "success": True,
        "code": code_upper,
        "credits_added": credits,
        "description": promo["description"],
        "message": f"Added {credits} credits to your account!",
    }
