"""
PitchLab - Credit Service
Handles credit deduction, balance checks, and monthly resets.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.user import User, CreditAccount, CreditTransaction, PlanTier
from app.core.config import settings


async def get_or_create_credit_account(user: User, db: AsyncSession) -> CreditAccount:
    result = await db.execute(
        select(CreditAccount).where(CreditAccount.user_id == user.id)
    )
    account = result.scalar_one_or_none()

    if not account:
        if user.plan == PlanTier.pro:
            monthly = settings.PRO_MONTHLY_CREDITS
        elif user.plan == PlanTier.starter:
            monthly = settings.STARTER_MONTHLY_CREDITS
        else:
            monthly = settings.FREE_MONTHLY_CREDITS
        )
        account = CreditAccount(
            user_id=user.id,
            balance=monthly,
            next_reset_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(account)
        await db.flush()

    return account


async def check_and_deduct(
    user: User,
    db: AsyncSession,
    cost: int,
    reason: str,
) -> CreditAccount:
    account = await get_or_create_credit_account(user, db)

    if account.next_reset_at:
        reset_time = account.next_reset_at.replace(tzinfo=None)
        if datetime.now() >= reset_time:
            await reset_monthly_credits(user, account, db)

    if account.balance < cost:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "insufficient_credits",
                "message": f"This action costs {cost} credits. You have {account.balance} remaining.",
                "balance": account.balance,
                "required": cost,
            },
        )

    account.balance -= cost
    account.lifetime_used += cost

    transaction = CreditTransaction(
        account_id=account.id,
        amount=-cost,
        reason=reason,
    )
    db.add(transaction)
    await db.flush()

    return account


async def add_credits(
    user: User,
    db: AsyncSession,
    amount: int,
    reason: str,
) -> CreditAccount:
    account = await get_or_create_credit_account(user, db)
    account.balance += amount

    transaction = CreditTransaction(
        account_id=account.id,
        amount=amount,
        reason=reason,
    )
    db.add(transaction)
    await db.flush()
    return account


async def reset_monthly_credits(
    user: User,
    account: CreditAccount,
    db: AsyncSession,
) -> None:
    if user.plan == PlanTier.pro:
            monthly = settings.PRO_MONTHLY_CREDITS
        elif user.plan == PlanTier.starter:
            monthly = settings.STARTER_MONTHLY_CREDITS
        else:
            monthly = settings.FREE_MONTHLY_CREDITS

    diff = monthly - account.balance
    if diff > 0:
        transaction = CreditTransaction(
            account_id=account.id,
            amount=diff,
            reason="monthly_reset",
        )
        db.add(transaction)

    account.balance = monthly
    account.last_reset_at = datetime.now(timezone.utc)
    account.next_reset_at = datetime.now(timezone.utc) + timedelta(days=30)
    await db.flush()


async def get_balance(user: User, db: AsyncSession) -> dict:
    account = await get_or_create_credit_account(user, db)

    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.account_id == account.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(10)
    )
    recent = result.scalars().all()

    return {
        "balance": account.balance,
        "lifetime_used": account.lifetime_used,
        "next_reset_at": account.next_reset_at.isoformat() if account.next_reset_at else None,
        "plan": user.plan,
       "monthly_allocation": (
            settings.PRO_MONTHLY_CREDITS if user.plan == PlanTier.pro
            else settings.STARTER_MONTHLY_CREDITS if user.plan == PlanTier.starter
            else settings.FREE_MONTHLY_CREDITS
        ),
        "recent_transactions": [
            {
                "amount": t.amount,
                "reason": t.reason,
                "created_at": t.created_at.isoformat(),
            }
            for t in recent
        ],
        "costs": {
            "lead_search":      settings.CREDIT_COST_LEAD_SEARCH,
            "audit":            settings.CREDIT_COST_AUDIT,
            "pitch_generation": settings.CREDIT_COST_PITCH_GENERATION,
            "message_send":     settings.CREDIT_COST_MESSAGE_SEND,
        },
    }
