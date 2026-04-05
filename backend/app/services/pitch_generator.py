"""
PitchLab - AI Pitch Generator
Generates cold email, cold call script, and SMS outreach using AI.
Uses Groq (fast) with Anthropic fallback.
"""

import httpx
import json
import re
from typing import Dict, Any, Optional
from app.core.config import settings


# ─── Internal prompt templates ────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert sales copywriter for a web design agency that sells websites 
to local trade businesses (plumbers, roofers, electricians, landscapers, dentists, etc.).

Your job is to write SHORT, SPECIFIC, PERSUASIVE outreach messages.

Rules:
- Always mention 1-2 SPECIFIC problems found in the audit
- Never be salesy or use corporate buzzwords
- Cold email: under 100 words. Subject line: under 8 words.
- Cold call script: conversational, under 150 words
- SMS: under 60 words, very casual
- Tone: friendly, local, like a neighbor who knows websites
- Always end with a soft CTA (a question, not a command)
- Never use phrases like "I hope this email finds you well" or "synergy"

Return ONLY a JSON object with these keys: cold_email_subject, cold_email_body, cold_call_script, sms
No markdown, no explanation, just the JSON."""


def _build_pitch_prompt(business_name: str, niche: str, audit_summary: str, top_issues: list) -> str:
    issues_text = "\n".join(f"- {i}" for i in top_issues[:3]) if top_issues else "- No website found"

    return f"""Generate outreach messages for this local business:

Business Name: {business_name}
Business Type: {niche}
Website Score: See audit below

Top Problems Found:
{issues_text}

Audit Summary:
{audit_summary}

Write the cold email, cold call script, and SMS as if you're a local web designer who just ran this audit."""


# ─── Groq API call ────────────────────────────────────────────────────────────

async def _call_groq(prompt: str) -> str:
    """Call Groq's fast inference API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                "max_tokens": 1000,
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# ─── Anthropic API call ───────────────────────────────────────────────────────

async def _call_anthropic(prompt: str) -> str:
    """Call Anthropic Claude API as fallback."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


# ─── Mock pitches for dev/demo ────────────────────────────────────────────────

def _mock_pitches(business_name: str, niche: str, top_issues: list) -> Dict[str, str]:
    issue_1 = top_issues[0] if top_issues else "no website"
    first_name = business_name.split()[0]

    return {
        "cold_email_subject": f"Quick question about {business_name}",
        "cold_email_body": (
            f"Hi there,\n\n"
            f"I was looking up {niche}s in your area and noticed {business_name} "
            f"has {issue_1.lower()}.\n\n"
            f"I build websites for local {niche}s that actually show up on Google — "
            f"usually takes about a week to go live.\n\n"
            f"Would a quick 10-minute call this week make sense?\n\n"
            f"— Brandon"
        ),
        "cold_call_script": (
            f"Hey, is this {first_name}? \n\n"
            f"Great — my name's Brandon, I'm a local web designer. I was doing some research "
            f"on {niche}s in the area and I pulled up {business_name}.\n\n"
            f"I noticed {issue_1.lower()}. I work with a handful of {niche}s around here and "
            f"that's usually the main reason they're not showing up when people Google them.\n\n"
            f"I put together a free audit of your online presence — would you have 10 minutes "
            f"this week for me to walk you through what I found?\n\n"
            f"[If yes] → Perfect, I'll send you the report now so you can see exactly what we're dealing with."
        ),
        "sms": (
            f"Hey, this is Brandon — local web designer. "
            f"Ran a quick audit on {business_name} and found some things hurting your Google ranking. "
            f"Worth a quick chat? I can send the report over."
        ),
    }


# ─── JSON parsing helper ──────────────────────────────────────────────────────

def _parse_pitch_json(raw: str) -> Optional[Dict[str, str]]:
    """Safely parse JSON from AI response, handling markdown fences."""
    # Strip ```json ... ``` fences if present
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


# ─── Main public function ─────────────────────────────────────────────────────

async def generate_pitches(
    business_name: str,
    niche: str,
    audit_summary: str,
    top_issues: list,
) -> Dict[str, str]:
    """
    Generate cold email, cold call script, and SMS for a lead.
    Returns a dict with keys: cold_email_subject, cold_email_body, cold_call_script, sms
    """
    prompt = _build_pitch_prompt(business_name, niche, audit_summary, top_issues)

    # Try Groq first (fastest)
    if settings.GROQ_API_KEY:
        try:
            raw = await _call_groq(prompt)
            parsed = _parse_pitch_json(raw)
            if parsed:
                return parsed
        except Exception as e:
            print(f"[PitchGen] Groq failed: {e}")

    # Try Anthropic as fallback
    if settings.ANTHROPIC_API_KEY:
        try:
            raw = await _call_anthropic(prompt)
            parsed = _parse_pitch_json(raw)
            if parsed:
                return parsed
        except Exception as e:
            print(f"[PitchGen] Anthropic failed: {e}")

    # Final fallback: mock data
    return _mock_pitches(business_name, niche, top_issues)
