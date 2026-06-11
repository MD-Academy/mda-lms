"""
Email sending via Resend + branded HTML templates.

All sends go through send_email(), which NEVER raises — a mail failure must
not break account creation or any other flow. It returns True/False and logs
the reason so failures are visible to us (not silent).

Required env:
  RESEND_API_KEY   - Resend API key (Render env; never in code)
Optional env (sensible defaults):
  EMAIL_FROM       - e.g. 'Medical Doctor Academy <noreply@medicaldoctor-studies.com>'
  EMAIL_REPLY_TO   - e.g. 'info@medicaldoctor-studies.com'
  STUDENT_URL      - student portal login URL
  LOGO_URL         - public https URL to the logo (emails need an absolute URL)
"""

import os
import re
import logging

import httpx

logger = logging.getLogger("mda.emails")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Medical Doctor Academy <noreply@medicaldoctor-studies.com>")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO", "info@medicaldoctor-studies.com")
STUDENT_URL = os.environ.get("STUDENT_URL", "https://students.medicaldoctor-studies.com").rstrip("/")
LOGO_URL = os.environ.get("LOGO_URL", f"{STUDENT_URL}/assets/images/mda-logo.png")
OFFICE_EMAIL = "info@medicaldoctor-studies.com"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    """Basic but solid RFC-ish format check."""
    return bool(_EMAIL_RE.match((email or "").strip()))


def _esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def send_email(to: str, subject: str, html: str) -> bool:
    """Send one email through Resend. Returns True on success, False otherwise.
    Never raises."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s (%r)", to, subject)
        return False
    if not is_valid_email(to):
        logger.warning("Refusing to send to invalid address: %r", to)
        return False
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": EMAIL_FROM,
                "to": [to],
                "reply_to": EMAIL_REPLY_TO,
                "subject": subject,
                "html": html,
            },
            timeout=15.0,
        )
        if resp.status_code >= 400:
            logger.error("Resend rejected email to %s: %s %s", to, resp.status_code, resp.text)
            return False
        return True
    except Exception as e:  # network, timeout, etc.
        logger.error("Failed to send email to %s: %s", to, e)
        return False


# ── TEMPLATES ────────────────────────────────────────────────

def _wrap(title: str, body_html: str) -> str:
    """Branded shell: navy header with logo, white card, footer."""
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#eef2f7;font-family:Helvetica,Arial,sans-serif;color:#1e293b;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f7;padding:28px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 2px 10px rgba(15,23,42,.06);">
        <tr><td style="background:#0d2a52;padding:26px 0;text-align:center;">
          <img src="{_esc(LOGO_URL)}" alt="Medical Doctor International Academy" width="64" height="64" style="display:inline-block;border-radius:50%;background:#fff;">
          <div style="color:#ffffff;font-size:16px;font-weight:700;margin-top:10px;letter-spacing:.3px;">Medical Doctor International Academy</div>
        </td></tr>
        <tr><td style="padding:32px 34px;">
          <h1 style="margin:0 0 16px;font-size:21px;color:#0d2a52;">{_esc(title)}</h1>
          {body_html}
        </td></tr>
        <tr><td style="padding:18px 34px 28px;border-top:1px solid #eef2f7;color:#94a3b8;font-size:12px;line-height:1.6;">
          For help or to request an extension, contact the office at
          <a href="mailto:{OFFICE_EMAIL}" style="color:#2563eb;text-decoration:none;">{OFFICE_EMAIL}</a>.<br>
          This is an automated message from the Medical Doctor International Academy learning portal.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def _button(label: str, url: str) -> str:
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0;">'
            f'<tr><td style="border-radius:9px;background:#2563eb;">'
            f'<a href="{_esc(url)}" style="display:inline-block;padding:13px 26px;color:#fff;'
            f'font-weight:700;font-size:15px;text-decoration:none;border-radius:9px;">{_esc(label)}</a>'
            f'</td></tr></table>')


def welcome_email(full_name: str, email: str, password: str, expiry_date: str = None):
    """Returns (subject, html) for the new-student welcome + credentials email."""
    first = (full_name or "there").strip().split()[0] if full_name else "there"
    expiry_line = ""
    if expiry_date:
        expiry_line = (f'<p style="margin:0 0 16px;font-size:15px;line-height:1.6;">'
                       f'Your access is valid until <strong>{_esc(expiry_date)}</strong>. '
                       f'For renewals or extensions, contact the office.</p>')
    body = f"""\
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">Dear {_esc(first)},</p>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        Welcome to the Medical Doctor International Academy learning portal. Your account is ready
        — here are your login details:</p>
      <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#f7f9fc;border:1px solid #e6ecf4;border-radius:10px;margin:6px 0 4px;">
        <tr><td style="padding:16px 18px;font-size:15px;line-height:1.9;">
          <strong>Portal:</strong> <a href="{_esc(STUDENT_URL)}" style="color:#2563eb;text-decoration:none;">{_esc(STUDENT_URL)}</a><br>
          <strong>Username:</strong> {_esc(email)}<br>
          <strong>Password:</strong> <span style="font-family:monospace;background:#fff;border:1px solid #e6ecf4;border-radius:5px;padding:2px 7px;">{_esc(password)}</span>
        </td></tr>
      </table>
      {_button("Log in to the portal", STUDENT_URL)}
      <p style="margin:0 0 16px;font-size:14px;line-height:1.6;color:#475569;">
        For your security, please sign in and change your password from the
        <strong>My Profile</strong> page. You can also enable two-factor authentication there.</p>
      {expiry_line}"""
    return ("Welcome to Medical Doctor International Academy — your login details", _wrap("Welcome aboard 👋", body))
