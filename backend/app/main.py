"""
PitchLab - Main FastAPI Application
Entry point for the PitchLab micro-SaaS platform.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api import leads, audits, pitches, messaging, credits, auth, billing


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown cleanup (if needed)
    await engine.dispose()


app = FastAPI(
    title="PitchLab API",
    description="Lead generation & outreach automation for web designers",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — adjust origins for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route registration
app.include_router(auth.router,      prefix="/api/auth",      tags=["Auth"])
app.include_router(leads.router,     prefix="/api/leads",     tags=["Leads"])
app.include_router(audits.router,    prefix="/api/audits",    tags=["Audits"])
app.include_router(pitches.router,   prefix="/api/pitches",   tags=["Pitches"])
app.include_router(messaging.router, prefix="/api/messaging", tags=["Messaging"])
app.include_router(credits.router,   prefix="/api/credits",   tags=["Credits"])
app.include_router(billing.router,   prefix="/api/billing",   tags=["Billing"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
