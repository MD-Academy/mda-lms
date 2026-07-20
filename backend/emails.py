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
EMAIL_FROM = os.environ.get("EMAIL_FROM", "Medical Doctor Academy <noreply@updates.medicaldoctor-studies.com>")
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO", "info@medicaldoctor-studies.com")
STUDENT_URL = os.environ.get("STUDENT_URL", "https://students.medicaldoctor-studies.com").rstrip("/")
LOGO_URL = os.environ.get("LOGO_URL", f"{STUDENT_URL}/assets/images/favicon.png")
RESET_URL = f"{STUDENT_URL}/reset.html"
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


def send_batch(messages: list) -> int:
    """Send many emails via Resend's batch endpoint (max 100 per call; we chunk).
    messages = [{"to": str, "subject": str, "html": str}, ...].
    Returns how many were accepted. Never raises."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping batch of %d emails", len(messages))
        return 0
    valid = [m for m in messages if is_valid_email(m.get("to", ""))]
    sent = 0
    for i in range(0, len(valid), 100):
        chunk = valid[i:i + 100]
        payload = [{
            "from": EMAIL_FROM,
            "to": [m["to"]],
            "reply_to": EMAIL_REPLY_TO,
            "subject": m["subject"],
            "html": m["html"],
        } for m in chunk]
        try:
            resp = httpx.post(
                "https://api.resend.com/emails/batch",
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=30.0,
            )
            if resp.status_code >= 400:
                logger.error("Resend batch rejected (%d emails): %s %s", len(chunk), resp.status_code, resp.text)
                continue
            sent += len(chunk)
        except Exception as e:
            logger.error("Failed to send batch of %d emails: %s", len(chunk), e)
    return sent


def send_email(to: str, subject: str, html: str, attachments: list = None) -> bool:
    """Send one email through Resend. Returns True on success, False otherwise.
    Never raises.

    attachments (optional): [{"filename": str, "content": <base64 str>}].
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping email to %s (%r)", to, subject)
        return False
    if not is_valid_email(to):
        logger.warning("Refusing to send to invalid address: %r", to)
        return False
    payload = {
        "from": EMAIL_FROM,
        "to": [to],
        "reply_to": EMAIL_REPLY_TO,
        "subject": subject,
        "html": html,
    }
    if attachments:
        payload["attachments"] = attachments
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30.0,
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


def _greeting(full_name: str) -> str:
    first = (full_name or "there").strip().split()[0] if full_name else "there"
    return f'<p style="margin:0 0 16px;font-size:15px;line-height:1.6;">Dear {_esc(first)},</p>'


def announcement_email(full_name: str, title: str, body_text: str):
    """Returns (subject, html) for a new-announcement notification."""
    safe_body = _esc(body_text).replace("\n", "<br>")
    body = f"""\
      {_greeting(full_name)}
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">A new announcement has been posted:</p>
      <div style="background:#f7f9fc;border:1px solid #e6ecf4;border-left:4px solid #2563eb;border-radius:10px;padding:16px 18px;margin:6px 0 4px;">
        <div style="font-size:16px;font-weight:700;color:#0d2a52;margin-bottom:6px;">{_esc(title)}</div>
        <div style="font-size:14px;line-height:1.6;color:#334155;">{safe_body}</div>
      </div>
      {_button("Open the portal", STUDENT_URL)}
      <p style="margin:0;font-size:12px;color:#94a3b8;">You're receiving this because announcement emails are on in your profile. You can turn them off under <strong>My Profile → Notifications</strong>.</p>"""
    return (f"New announcement: {title}", _wrap("📣 New announcement", body))


def schedule_email(full_name: str, topic: str, date_str: str, subject_name: str = None, details: str = None):
    """Returns (subject, html) for a new scheduled-session notification."""
    rows = f'<strong>Topic:</strong> {_esc(topic)}<br><strong>Date:</strong> {_esc(date_str)}'
    if subject_name:
        rows += f'<br><strong>Subject:</strong> {_esc(subject_name)}'
    if details:
        rows += f'<br><strong>Details:</strong> {_esc(details)}'
    body = f"""\
      {_greeting(full_name)}
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">A new session has been added to the calendar:</p>
      <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#f7f9fc;border:1px solid #e6ecf4;border-radius:10px;margin:6px 0 4px;">
        <tr><td style="padding:16px 18px;font-size:15px;line-height:1.9;color:#334155;">{rows}</td></tr>
      </table>
      {_button("View your calendar", STUDENT_URL + "/dashboard.html")}
      <p style="margin:0;font-size:12px;color:#94a3b8;">You're receiving this because schedule emails are on in your profile. You can turn them off under <strong>My Profile → Notifications</strong>.</p>"""
    return (f"New session scheduled: {topic}", _wrap("🗓️ New scheduled session", body))


def _login_help(email: str) -> str:
    """Shared footer block: username reminder + reset link (no password)."""
    return (f'<p style="margin:14px 0 0;font-size:13px;line-height:1.6;color:#475569;">'
            f'Your username is <strong>{_esc(email)}</strong>. '
            f'Forgot your password? <a href="{_esc(RESET_URL)}" style="color:#2563eb;">Reset it here</a>.</p>')


def inactivity_email(full_name: str, email: str, days: int):
    """Returns (subject, html) for an inactivity nudge (7/15/30 days)."""
    body = f"""\
      {_greeting(full_name)}
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        We noticed it's been about <strong>{days} days</strong> since you last signed in to the
        Medical Doctor International Academy portal. Your lessons, recordings and materials are
        waiting whenever you're ready to continue.</p>
      {_button("Log in and continue", STUDENT_URL)}
      {_login_help(email)}"""
    return ("We've saved your spot — continue your studies", _wrap("We miss you 👋", body))


def attendance_low_email(full_name: str, email: str, low_courses: list, threshold):
    """Returns (subject, html). low_courses = [(course_name, pct), ...]."""
    rows = "".join(
        f'<li style="margin:4px 0;"><strong>{_esc(name)}</strong> — {pct}% attended</li>'
        for name, pct in low_courses
    )
    body = f"""\
      {_greeting(full_name)}
      <p style="margin:0 0 12px;font-size:15px;line-height:1.6;">
        This is a friendly reminder that your attendance has dropped below the required
        <strong>{int(threshold)}%</strong>:</p>
      <ul style="margin:0 0 16px;padding-left:20px;font-size:15px;line-height:1.7;color:#334155;">{rows}</ul>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        Regular attendance is important for your progress. Please make sure to attend your
        upcoming classes, and contact the office if you need to discuss any missed sessions.</p>
      {_button("Open your portal", STUDENT_URL)}
      {_login_help(email)}"""
    return ("Attendance reminder — please attend your classes", _wrap("📅 Attendance reminder", body))


def grade_low_email(full_name: str, email: str, low_courses: list, threshold):
    """Returns (subject, html). low_courses = [(course_name, overall_pct), ...]."""
    rows = "".join(
        f'<li style="margin:4px 0;"><strong>{_esc(name)}</strong> — current overall {pct}%</li>'
        for name, pct in low_courses
    )
    body = f"""\
      {_greeting(full_name)}
      <p style="margin:0 0 12px;font-size:15px;line-height:1.6;">
        This is an important reminder that your current overall grade is below the required
        <strong>{int(threshold)}%</strong>:</p>
      <ul style="margin:0 0 16px;padding-left:20px;font-size:15px;line-height:1.7;color:#334155;">{rows}</ul>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        Please review your results in the portal, focus on upcoming exams and presentations,
        and contact the office if you'd like support. Acting now can still turn this around.</p>
      {_button("Open your portal", STUDENT_URL)}
      {_login_help(email)}"""
    return ("Grade reminder — your overall grade is below the required minimum", _wrap("📉 Grade reminder", body))


def expiry_email(full_name: str, email: str, expiry_date: str, days_left: int):
    """Returns (subject, html) for the one-time 'expires in ~7 days' reminder."""
    when = "today" if days_left == 0 else (f"in {days_left} day" + ("" if days_left == 1 else "s"))
    body = f"""\
      {_greeting(full_name)}
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        This is a friendly reminder that your access to the portal will expire <strong>{when}</strong>
        (on <strong>{_esc(expiry_date)}</strong>).</p>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        If you've completed your studies, no action is needed. If you need to extend your access,
        please contact the office at
        <a href="mailto:{OFFICE_EMAIL}" style="color:#2563eb;">{OFFICE_EMAIL}</a>.</p>
      {_button("Log in to the portal", STUDENT_URL)}
      {_login_help(email)}"""
    return ("Your portal access is expiring soon", _wrap("⏳ Access expiring soon", body))


_TICKET_STATUS_LABELS = {"open": "Open", "in_progress": "In Progress", "completed": "Completed"}


def teacher_feedback_email(full_name: str, teacher_name: str, feedback_text: str, course_name: str = None):
    """Returns (subject, html) for the student: a teacher wrote them feedback.

    Not tied to an exam or a test — a teacher writes whenever they have
    something worth telling the student. The full text is in the email so
    the student can read it without signing in.
    """
    safe_body = _esc(feedback_text).replace("\n", "<br>")
    about = f' on <strong>{_esc(course_name)}</strong>' if course_name else ""
    who = _esc(teacher_name or "One of your teachers")
    body = f"""\
      {_greeting(full_name)}
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        <strong>{who}</strong> has written you some feedback{about}:</p>
      <div style="background:#f7f9fc;border:1px solid #e6ecf4;border-left:4px solid #b01455;border-radius:10px;padding:16px 18px;margin:6px 0 4px;">
        <div style="font-size:15px;line-height:1.7;color:#334155;">{safe_body}</div>
      </div>
      <p style="margin:16px 0 0;font-size:14px;line-height:1.6;color:#475569;">
        Please take a moment to read it. If anything is unclear, speak to your teacher in the next class
        or contact the office — we're here to help you.</p>
      {_button("See all your feedback", STUDENT_URL + "/feedback.html")}
      <p style="margin:0;font-size:12px;color:#94a3b8;">All the feedback your teachers write for you is kept in your portal under <strong>Teacher Feedback</strong>.</p>"""
    subject = f"Feedback from {teacher_name}" if teacher_name else "New feedback from your teacher"
    return (subject, _wrap("💬 Feedback from your teacher", body))


def ticket_opened_email(student_name: str, title: str, body_text: str):
    """Returns (subject, html) for the office: a student opened a new ticket."""
    safe_body = _esc(body_text).replace("\n", "<br>")
    body = f"""\
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        <strong>{_esc(student_name)}</strong> opened a new support ticket:</p>
      <div style="background:#f7f9fc;border:1px solid #e6ecf4;border-left:4px solid #2563eb;border-radius:10px;padding:16px 18px;margin:6px 0 4px;">
        <div style="font-size:16px;font-weight:700;color:#0d2a52;margin-bottom:6px;">{_esc(title)}</div>
        <div style="font-size:14px;line-height:1.6;color:#334155;">{safe_body}</div>
      </div>
      {_button("Open in the admin portal", "https://admin.medicaldoctor-studies.com/tickets.html")}
      <p style="margin:0;font-size:13px;color:#94a3b8;">Reply and update the status from the Tickets section.</p>"""
    return (f"New support ticket: {title}", _wrap("🎫 New support ticket", body))


def ticket_office_reply_email(student_name: str, title: str):
    """Returns (subject, html) for the office: a student replied on a ticket."""
    body = f"""\
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        <strong>{_esc(student_name)}</strong> replied on their support ticket:</p>
      <div style="background:#f7f9fc;border:1px solid #e6ecf4;border-left:4px solid #2563eb;border-radius:10px;padding:14px 18px;margin:6px 0 4px;">
        <div style="font-size:15px;font-weight:700;color:#0d2a52;">{_esc(title)}</div>
      </div>
      {_button("Open in the admin portal", "https://admin.medicaldoctor-studies.com/tickets.html")}"""
    return (f"New reply on ticket: {title}", _wrap("🎫 Ticket updated", body))


def ticket_update_email(student_name: str, title: str, reply_text: str = None, status: str = None):
    """Returns (subject, html) for the student: the office replied and/or changed status."""
    parts = []
    if reply_text:
        parts.append(f"""\
      <p style="margin:0 0 12px;font-size:15px;line-height:1.6;">The office responded to your ticket:</p>
      <div style="background:#f7f9fc;border:1px solid #e6ecf4;border-left:4px solid #2563eb;border-radius:10px;padding:14px 18px;margin:6px 0 14px;">
        <div style="font-size:14px;line-height:1.6;color:#334155;">{_esc(reply_text).replace(chr(10), '<br>')}</div>
      </div>""")
    if status:
        label = _TICKET_STATUS_LABELS.get(status, status)
        color = {"open": "#dc2626", "in_progress": "#2563eb", "completed": "#16a34a"}.get(status, "#475569")
        parts.append(f"""\
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">Your ticket's status is now
        <strong style="color:{color};">{_esc(label)}</strong>.</p>""")
    body = f"""\
      {_greeting(student_name)}
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">There's an update on your support ticket
        <strong>“{_esc(title)}”</strong>.</p>
      {''.join(parts)}
      {_button("View your ticket", STUDENT_URL + "/support.html")}"""
    return (f"Update on your ticket: {title}", _wrap("🎫 Ticket update", body))


def diploma_email(full_name: str, course_name: str):
    """Returns (subject, html) for the congratulations email that carries the
    diploma + recommendation letter as attachments."""
    body = f"""\
      {_greeting(full_name)}
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        Congratulations on completing the <strong>{_esc(course_name)}</strong> at the
        Medical Doctor International Academy! 🎓 It has been a pleasure to support you in your
        preparation for medical studies.</p>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        Attached to this email you'll find two documents:</p>
      <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background:#f7f9fc;border:1px solid #e6ecf4;border-radius:10px;margin:6px 0 14px;">
        <tr><td style="padding:16px 18px;font-size:15px;line-height:1.9;color:#334155;">
          📜 <strong>Your Premedical Studies Diploma</strong><br>
          ✉️ <strong>Your Letter of Recommendation</strong>
        </td></tr>
      </table>
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        You can also download them anytime from the <strong>My Profile</strong> page in your student portal.</p>
      {_button("Open the portal", STUDENT_URL)}
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        We wish you every success on the next step of your journey toward becoming a doctor.</p>"""
    return ("🎓 Congratulations — your diploma & recommendation letter", _wrap("Congratulations! 🎓", body))


def reset_link_email(full_name: str, action_link: str):
    """Returns (subject, html) for an on-demand password-reset link."""
    body = f"""\
      {_greeting(full_name)}
      <p style="margin:0 0 16px;font-size:15px;line-height:1.6;">
        We received a request to reset your password. Click the button below to choose a new one.
        If you didn't request this, you can safely ignore this email — your password won't change.</p>
      {_button("Reset my password", action_link)}
      <p style="margin:0;font-size:13px;color:#94a3b8;">For your security, this link expires shortly. If it stops working, request a new one from the portal.</p>"""
    return ("Reset your portal password", _wrap("🔑 Password reset", body))
