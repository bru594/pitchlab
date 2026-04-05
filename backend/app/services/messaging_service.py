"""
PitchLab - Messaging Service
Handles email dispatch via SMTP and SMS (mock/Twilio).
Tracks opens via pixel beacon (optional).
"""

import smtplib
import ssl
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.models.user import Message, MessageStatus, Lead, OutreachSequence, SequenceStatus


# ─── Email sending ────────────────────────────────────────────────────────────

async def send_email(
    to_email: str,
    subject: str,
    body: str,
    from_name: str = "Brandon",
) -> bool:
    """
    Send an email via SMTP.
    Returns True on success, False on failure.
    Runs SMTP in a thread to avoid blocking the event loop.
    """
    if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD]):
        print(f"[Email] SMTP not configured — would send to {to_email}: '{subject}'")
        return True  # Mock success in dev

    def _send():
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{from_name} <{settings.FROM_EMAIL or settings.SMTP_USER}>"
        msg["To"]      = to_email

        # Plain text part
        msg.attach(MIMEText(body, "plain"))

        # HTML part (simple wrapping)
        html_body = body.replace("\n", "<br>")
        html = f"""
        <html><body style="font-family:Georgia,serif;max-width:600px;margin:0 auto;padding:20px;color:#333;">
        {html_body}
        </body></html>
        """
        msg.attach(MIMEText(html, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())

    try:
        await asyncio.get_event_loop().run_in_executor(None, _send)
        return True
    except Exception as e:
        print(f"[Email] Send failed to {to_email}: {e}")
        return False


# ─── SMS sending (mock — plug in Twilio) ──────────────────────────────────────

async def send_sms(to_phone: str, body: str) -> bool:
    """
    Send SMS via Twilio (or mock in dev).
    To enable real SMS: pip install twilio, add TWILIO_* env vars.
    """
    # Mock implementation — log and return success
    print(f"[SMS] Would send to {to_phone}: {body[:80]}...")
    return True

    # Real Twilio implementation (uncomment and add env vars):
    # from twilio.rest import Client
    # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    # message = client.messages.create(
    #     body=body,
    #     from_=settings.TWILIO_FROM_NUMBER,
    #     to=to_phone,
    # )
    # return message.sid is not None


# ─── Message record management ────────────────────────────────────────────────

async def mark_message_sent(message: Message, db: AsyncSession) -> None:
    """Update message status to sent."""
    message.status = MessageStatus.sent
    message.sent_at = datetime.now(timezone.utc)
    await db.flush()


async def mark_message_opened(message_id: int, db: AsyncSession) -> None:
    """Track when a message is opened (via pixel/webhook)."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if msg and msg.status == MessageStatus.sent:
        msg.status  = MessageStatus.opened
        msg.opened_at = datetime.now(timezone.utc)
        await db.commit()


async def mark_message_replied(message_id: int, db: AsyncSession) -> None:
    """Mark as replied and stop the sequence."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        return

    msg.status     = MessageStatus.replied
    msg.replied_at = datetime.now(timezone.utc)

    # Stop the sequence
    if msg.sequence_id:
        seq_result = await db.execute(
            select(OutreachSequence).where(OutreachSequence.id == msg.sequence_id)
        )
        seq = seq_result.scalar_one_or_none()
        if seq:
            seq.status = SequenceStatus.stopped

    await db.commit()


# ─── Sequence step dispatch ───────────────────────────────────────────────────

async def dispatch_sequence_step(
    sequence: OutreachSequence,
    lead: Lead,
    message: Message,
    db: AsyncSession,
) -> bool:
    """
    Send the next step in an outreach sequence.
    Returns True if sent, False on failure.
    """
    # Don't send if sequence was stopped (e.g., reply received)
    if sequence.status != SequenceStatus.active:
        return False

    success = False

    if message.channel == "email" and lead.website:
        # In production, extract email from website or use a stored contact email
        # For now we use a placeholder
        email = f"contact@{lead.website.replace('https://', '').replace('http://', '').split('/')[0]}"
        success = await send_email(email, message.subject or "Quick question", message.body)
    elif message.channel == "sms" and lead.phone:
        success = await send_sms(lead.phone, message.body)

    if success:
        await mark_message_sent(message, db)
        sequence.current_step += 1
        if sequence.current_step >= sequence.total_steps:
            sequence.status = SequenceStatus.completed
        await db.flush()

    return success
