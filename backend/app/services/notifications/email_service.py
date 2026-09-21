"""
Email Notification Service for AI-HOS.

Provides:
- Medicine reminder emails (HTML)
- Appointment reminder emails
- Graceful no-op if SMTP not configured (SMTP_ENABLED=false or missing credentials)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import fastapi-mail — silent at startup if not installed.
# Warning is emitted at first actual send attempt, not at import time.
try:
    from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
    HAS_FASTMAIL = True
except ImportError:
    ConnectionConfig = FastMail = MessageSchema = MessageType = None  # type: ignore[assignment,misc]
    HAS_FASTMAIL = False


def _get_mail_config():
    """Build FastMail config from app settings. Returns None if SMTP is not enabled."""
    try:
        from app.core.config import settings
        if not getattr(settings, "SMTP_ENABLED", False):
            return None
        if not getattr(settings, "SMTP_USER", None):
            return None
        return ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USER,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
            MAIL_PORT=int(getattr(settings, "SMTP_PORT", 587)),
            MAIL_SERVER=settings.SMTP_HOST,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )
    except Exception as exc:
        logger.warning("SMTP config error: %s — email disabled", exc)
        return None


# ─── HTML Email Templates ─────────────────────────────────────────────────────

def _reminder_html(patient_name: str, medications: list[dict], reminder_time: str) -> str:
    med_rows = "".join(
        f"<tr><td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>"
        f"<strong>{m.get('name', '—')}</strong></td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>{m.get('dose', '—')}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>{m.get('frequency', '—')}</td></tr>"
        for m in medications
    )
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>Medication Reminder — AI-HOS</title></head>
<body style='margin:0;padding:0;background:#f8fafc;font-family:Inter,Arial,sans-serif'>
  <table width='100%' cellpadding='0' cellspacing='0'>
    <tr><td align='center' style='padding:32px 16px'>
      <table width='560' cellpadding='0' cellspacing='0'
             style='background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08)'>

        <!-- Header -->
        <tr><td style='background:linear-gradient(135deg,#1e40af,#3b82f6);padding:28px 32px'>
          <h1 style='margin:0;color:#ffffff;font-size:20px;font-weight:700'>💊 Medication Reminder</h1>
          <p style='margin:6px 0 0;color:#bfdbfe;font-size:13px'>AI-HOS Patient Portal</p>
        </td></tr>

        <!-- Body -->
        <tr><td style='padding:28px 32px'>
          <p style='margin:0 0 16px;font-size:15px;color:#374151'>
            Hi <strong>{patient_name}</strong>,<br/>
            This is your medication reminder for <strong>{reminder_time}</strong>.
          </p>

          <table width='100%' cellpadding='0' cellspacing='0'
                 style='border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-bottom:20px'>
            <tr style='background:#eff6ff'>
              <th style='padding:8px 12px;text-align:left;font-size:12px;color:#1e40af;font-weight:600'>Medication</th>
              <th style='padding:8px 12px;text-align:left;font-size:12px;color:#1e40af;font-weight:600'>Dose</th>
              <th style='padding:8px 12px;text-align:left;font-size:12px;color:#1e40af;font-weight:600'>Frequency</th>
            </tr>
            {med_rows if med_rows else "<tr><td colspan='3' style='padding:12px;color:#9ca3af;text-align:center'>No medications listed</td></tr>"}
          </table>

          <div style='background:#fef9c3;border:1px solid #fde047;border-radius:8px;padding:12px 16px;margin-bottom:20px'>
            <p style='margin:0;font-size:13px;color:#713f12'>
              ⚠️ <strong>Important:</strong> Take your medications as prescribed.
              Contact your doctor if you experience any adverse effects.
            </p>
          </div>

          <p style='margin:0;font-size:13px;color:#6b7280'>
            You can manage your reminders in the <a href='#' style='color:#3b82f6'>AI-HOS Patient Portal</a>.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style='background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0'>
          <p style='margin:0;font-size:11px;color:#9ca3af;text-align:center'>
            AI-HOS Healthcare Operating System | This is an automated reminder.<br/>
            Do not reply to this email.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def _appointment_html(patient_name: str, doctor_name: str, appointment_time: str, appointment_type: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset='utf-8'><title>Appointment Reminder — AI-HOS</title></head>
<body style='margin:0;padding:0;background:#f8fafc;font-family:Inter,Arial,sans-serif'>
  <table width='100%' cellpadding='0' cellspacing='0'>
    <tr><td align='center' style='padding:32px 16px'>
      <table width='560' cellpadding='0' cellspacing='0'
             style='background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08)'>
        <tr><td style='background:linear-gradient(135deg,#059669,#34d399);padding:28px 32px'>
          <h1 style='margin:0;color:#ffffff;font-size:20px;font-weight:700'>📅 Appointment Reminder</h1>
          <p style='margin:6px 0 0;color:#a7f3d0;font-size:13px'>AI-HOS Patient Portal</p>
        </td></tr>
        <tr><td style='padding:28px 32px'>
          <p style='margin:0 0 16px;font-size:15px;color:#374151'>
            Hi <strong>{patient_name}</strong>,
          </p>
          <div style='background:#ecfdf5;border:1px solid #6ee7b7;border-radius:12px;padding:20px;margin-bottom:20px'>
            <p style='margin:0 0 8px;font-size:13px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.05em'>Your Appointment</p>
            <p style='margin:0 0 4px;font-size:18px;font-weight:700;color:#065f46'>{appointment_time}</p>
            <p style='margin:0 0 4px;font-size:14px;color:#374151'>With: <strong>Dr. {doctor_name}</strong></p>
            <p style='margin:0;font-size:14px;color:#374151'>Type: {appointment_type}</p>
          </div>
          <p style='margin:0;font-size:13px;color:#6b7280'>
            Please arrive 10 minutes early. For telehealth, log in to the
            <a href='#' style='color:#059669'>AI-HOS Patient Portal</a> at your appointment time.
          </p>
        </td></tr>
        <tr><td style='background:#f8fafc;padding:16px 32px;border-top:1px solid #e2e8f0'>
          <p style='margin:0;font-size:11px;color:#9ca3af;text-align:center'>
            AI-HOS Healthcare Operating System | Automated notification. Do not reply.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ─── Public API ───────────────────────────────────────────────────────────────

async def send_reminder_email(
    to_email: str,
    patient_name: str,
    medications: list[dict[str, Any]],
    reminder_time: str,
) -> bool:
    """
    Send a medicine reminder email.

    Returns True if sent, False if SMTP not configured or send failed.
    Always safe to call — never raises.
    """
    if not HAS_FASTMAIL:
        logger.warning(
            "fastapi-mail not installed \u2014 email to %s skipped. "
            "Run: pip install fastapi-mail",
            to_email,
        )
        return False

    config = _get_mail_config()
    if not config:
        logger.debug("SMTP not configured — skipping reminder email to %s", to_email)
        return False

    try:
        html = _reminder_html(patient_name, medications, reminder_time)
        message = MessageSchema(
            subject=f"💊 Medication Reminder — {reminder_time} | AI-HOS",
            recipients=[to_email],
            body=html,
            subtype=MessageType.html,
        )
        fm = FastMail(config)
        await fm.send_message(message)
        logger.info("Reminder email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send reminder email to %s: %s", to_email, exc)
        return False


async def send_appointment_reminder_email(
    to_email: str,
    patient_name: str,
    doctor_name: str,
    appointment_time: str,
    appointment_type: str = "Consultation",
) -> bool:
    """
    Send an appointment reminder email.

    Returns True if sent, False if SMTP not configured or send failed.
    Always safe to call — never raises.
    """
    if not HAS_FASTMAIL:
        return False

    config = _get_mail_config()
    if not config:
        return False

    try:
        html = _appointment_html(patient_name, doctor_name, appointment_time, appointment_type)
        message = MessageSchema(
            subject=f"📅 Appointment Reminder — Dr. {doctor_name} | AI-HOS",
            recipients=[to_email],
            body=html,
            subtype=MessageType.html,
        )
        fm = FastMail(config)
        await fm.send_message(message)
        logger.info("Appointment reminder email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send appointment reminder email to %s: %s", to_email, exc)
        return False
