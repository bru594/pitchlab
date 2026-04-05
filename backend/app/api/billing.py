"""
PitchLab - Billing API Routes (Stripe)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User, PlanTier
from app.services.credit_service import add_credits

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str
    success_url: str
    cancel_url: str


@router.post("/create-checkout")
async def create_checkout_session(
    req: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.STRIPE_SECRET_KEY:
        return {
            "checkout_url": "https://checkout.stripe.com/mock",
            "session_id": "mock_session_123",
        }

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        price_id = settings.STRIPE_PRO_PRICE_ID

        if not user.stripe_customer_id:
            customer = stripe.Customer.create(email=user.email, name=user.full_name)
            user.stripe_customer_id = customer.id
            await db.flush()

        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=req.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=req.cancel_url,
            metadata={"user_id": str(user.id), "plan": req.plan},
        )
        return {"checkout_url": session.url, "session_id": session.id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.post("/cancel")
async def cancel_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription found")

    if not settings.STRIPE_SECRET_KEY:
        user.plan = PlanTier.free
        user.stripe_subscription_id = None
        return {"cancelled": True}

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.Subscription.modify(
            user.stripe_subscription_id,
            cancel_at_period_end=True,
        )
        return {"cancelled": True, "message": "Subscription will cancel at end of billing period"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    if not settings.STRIPE_SECRET_KEY:
        return {"received": True}

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        body = await request.body()
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session["metadata"].get("user_id", 0))
        plan = session["metadata"].get("plan", "pro")

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.plan = PlanTier.pro if plan == "pro" else PlanTier.free
            user.stripe_subscription_id = session.get("subscription")
            await add_credits(user, db, amount=settings.PRO_MONTHLY_CREDITS, reason="subscription_activation")

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        result = await db.execute(
            select(User).where(User.stripe_subscription_id == sub["id"])
        )
        user = result.scalar_one_or_none()
        if user:
            user.plan = PlanTier.free
            user.stripe_subscription_id = None

    return {"received": True}


@router.get("/plans")
async def get_plans():
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price_monthly": 0,
                "credits_monthly": settings.FREE_MONTHLY_CREDITS,
                "features": [
                    f"{settings.FREE_MONTHLY_CREDITS} credits/month",
                    "Lead search",
                    "Website audits",
                    "AI pitch generation",
                    "Email outreach",
                ],
            },
            {
                "id": "pro",
                "name": "Pro",
                "price_monthly": 49,
                "credits_monthly": settings.PRO_MONTHLY_CREDITS,
                "features": [
                    f"{settings.PRO_MONTHLY_CREDITS} credits/month",
                    "Everything in Free",
                    "Multi-step sequences",
                    "Open tracking",
                    "CSV export",
                    "Priority support",
                ],
            },
        ]
    }
