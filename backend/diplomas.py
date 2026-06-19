"""
Diploma + recommendation-letter generation.

Two PDFs are produced for a graduating student:
  • the Premedical Studies Diploma — an ornate certificate. We draw the
    Academy's artwork (assets/diploma-bg.*) full-page and overlay only the
    dynamic fields (name, date, optional final grade). Everything about WHERE
    those fields land lives in DIPLOMA_CONFIG below, so the layout can be
    re-tuned — or the whole background swapped — without touching the drawing
    code. If no background image is present we fall back to a clean vector
    certificate so the feature still works.
  • the Recommendation Letter — a formal letterhead document. The body text is
    written by Claude (see draft_recommendation) and reviewed/edited by the
    teacher before it ever gets here.

Nothing in here talks to the network or the database — callers pass plain data
in and get PDF bytes out. Pure + testable.
"""

import os
import io
import logging
from datetime import date

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle,
)

logger = logging.getLogger("mda.diplomas")

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "mda-logo.png")

# ── DIPLOMA LAYOUT ────────────────────────────────────────────
# Coordinates are FRACTIONS of the page (0..1), measured from the TOP-LEFT,
# so they're independent of the artwork's pixel resolution. Tune these to line
# the text up with your background, or drop in a new "background" file.
DIPLOMA_CONFIG = {
    # Base name (no extension) of the full-page certificate artwork in assets/,
    # landscape. Either diploma-bg.jpg or diploma-bg.png is picked up
    # automatically (JPG preferred — smaller file). If neither is present, a
    # built-in vector certificate is drawn instead.
    "background": "diploma-bg",

    # The student's name. "max_size" shrinks automatically so long names stay
    # on one line. "mask" paints a parchment rectangle first, to hide a
    # "STUDENT FULL NAME" placeholder baked into the artwork — set it to False
    # once you supply a clean background without that placeholder.
    "name": {
        "cx": 0.5, "cy": 0.405,
        "max_size": 54, "min_size": 26,
        "color": "#11335f", "font": "Times-Bold",
        "mask": True, "mask_w": 0.66, "mask_h": 0.085, "mask_color": "#FBF6E6",
    },

    # The date of issue — drawn in the gap just above the "DATE OF ISSUE" label
    # (below the wax seal).
    "date": {
        "cx": 0.5, "cy": 0.918,
        "size": 12, "color": "#11335f", "font": "Times-Roman",
    },

    # Optional teacher "final grade" line. This diploma design is full, so it's
    # OFF by default (the grade still appears in the recommendation letter and
    # the student's record). Set "show": True and tune cy to print it here.
    "grade": {
        "show": False,
        "cx": 0.5, "cy": 0.625,
        "size": 15, "color": "#7a1322", "font": "Times-Bold",
    },
}

NAVY = HexColor("#11335f")
CRIMSON = HexColor("#7a1322")
GOLD = HexColor("#b08d3f")
PARCHMENT = HexColor("#FBF6E6")


def _fmt_date(d=None) -> str:
    d = d or date.today()
    return d.strftime("%B %d, %Y")


def _fit_font(c, text, font, max_size, min_size, max_width):
    """Largest size (<= max_size, >= min_size) at which text fits max_width."""
    size = max_size
    while size > min_size and c.stringWidth(text, font, size) > max_width:
        size -= 1
    return size


def _background_path():
    """Locate the artwork. Accepts an explicit filename with extension, or a
    base name we resolve to .jpg/.jpeg/.png (JPG preferred — smaller)."""
    bg = (DIPLOMA_CONFIG.get("background") or "").strip()
    if not bg:
        return None
    if os.path.splitext(bg)[1]:               # already has an extension
        p = os.path.join(ASSETS_DIR, bg)
        return p if os.path.exists(p) else None
    for ext in (".jpg", ".jpeg", ".png"):     # probe by base name
        p = os.path.join(ASSETS_DIR, bg + ext)
        if os.path.exists(p):
            return p
    return None


def _draw_background(c, width, height):
    """Draw the certificate artwork full-page. Returns True if an image was used."""
    path = _background_path()
    if path:
        try:
            c.drawImage(path, 0, 0, width=width, height=height,
                        preserveAspectRatio=False, mask="auto")
            return True
        except Exception as e:
            logger.warning("Diploma background %s could not be drawn: %s", path, e)
    _draw_fallback_certificate(c, width, height)
    return False


def _draw_fallback_certificate(c, width, height):
    """A clean navy-bordered certificate, used until real artwork is supplied."""
    c.setFillColor(PARCHMENT)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    # Double border.
    c.setStrokeColor(NAVY)
    c.setLineWidth(10)
    c.rect(16, 16, width - 32, height - 32, fill=0, stroke=1)
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.rect(30, 30, width - 60, height - 60, fill=0, stroke=1)

    if os.path.exists(LOGO_PATH):
        try:
            lw = 120
            c.drawImage(LOGO_PATH, (width - lw) / 2, height - 150, width=lw, height=lw,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    c.setFillColor(CRIMSON)
    c.setFont("Times-Bold", 40)
    c.drawCentredString(width / 2, height - 215, "PREMEDICAL STUDIES DIPLOMA")
    c.setFillColor(NAVY)
    c.setFont("Times-Roman", 15)
    c.drawCentredString(width / 2, height - 245, "THIS IS TO CERTIFY THAT")
    # Body lines under the name area.
    c.setFont("Times-Roman", 15)
    by = height * 0.40
    c.drawCentredString(width / 2, by - 70, "has successfully completed the Premedical Studies Program")
    c.drawCentredString(width / 2, by - 95, "including Biology · Chemistry · Physics · Anatomy & Physiology · Medical English,")
    c.drawCentredString(width / 2, by - 120, "and has fulfilled all academic requirements of the program.")
    # Signature lines.
    c.setStrokeColor(NAVY)
    c.setLineWidth(1)
    c.line(width * 0.12, 110, width * 0.36, 110)
    c.line(width * 0.64, 110, width * 0.88, 110)
    c.setFont("Times-Bold", 12)
    c.drawCentredString(width * 0.24, 92, "Liat Epstein")
    c.drawCentredString(width * 0.76, 92, "Dr. Moshe Cohen")
    c.setFont("Times-Roman", 10)
    c.drawCentredString(width * 0.24, 78, "Academic Director")
    c.drawCentredString(width * 0.76, 78, "CEO")
    c.setFont("Times-Roman", 11)
    c.drawCentredString(width / 2, 64, "DATE OF ISSUE")


def build_diploma_pdf(student_name: str, issue_date=None, final_grade: str = None) -> bytes:
    """Return the diploma PDF as bytes."""
    buf = io.BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(width, height))

    _draw_background(c, width, height)

    def y_of(cy):  # fraction-from-top -> reportlab y (bottom-left origin)
        return height * (1 - cy)

    # Student name (with optional mask to cover a baked-in placeholder).
    name = (student_name or "").strip() or "Student"
    nc = DIPLOMA_CONFIG["name"]
    if nc.get("mask"):
        mw, mh = width * nc["mask_w"], height * nc["mask_h"]
        c.setFillColor(HexColor(nc["mask_color"]))
        c.rect((width - mw) / 2, y_of(nc["cy"]) - mh * 0.32, mw, mh, fill=1, stroke=0)
    size = _fit_font(c, name, nc["font"], nc["max_size"], nc["min_size"], width * 0.8)
    c.setFillColor(HexColor(nc["color"]))
    c.setFont(nc["font"], size)
    c.drawCentredString(width * nc["cx"], y_of(nc["cy"]), name)

    # Optional final grade / distinction line (off by default for this design).
    grade = (final_grade or "").strip()
    gc = DIPLOMA_CONFIG["grade"]
    if grade and gc.get("show"):
        c.setFillColor(HexColor(gc["color"]))
        c.setFont(gc["font"], gc["size"])
        c.drawCentredString(width * gc["cx"], y_of(gc["cy"]), grade)

    # Date of issue.
    dc = DIPLOMA_CONFIG["date"]
    c.setFillColor(HexColor(dc["color"]))
    c.setFont(dc["font"], dc["size"])
    c.drawCentredString(width * dc["cx"], y_of(dc["cy"]), _fmt_date(issue_date))

    c.showPage()
    c.save()
    return buf.getvalue()


# ── RECOMMENDATION LETTER ─────────────────────────────────────

def build_recommendation_pdf(student_name: str, body_text: str, issue_date=None,
                             signatory_name: str = "Liat Epstein",
                             signatory_title: str = "Academic Director") -> bytes:
    """Render the (teacher-approved) recommendation letter onto MDA letterhead."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=26 * mm, rightMargin=26 * mm,
        topMargin=20 * mm, bottomMargin=22 * mm,
        title="Letter of Recommendation",
    )
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "LetterBody", parent=styles["Normal"], fontName="Times-Roman",
        fontSize=12, leading=18, alignment=TA_JUSTIFY, spaceAfter=12,
    )
    head_style = ParagraphStyle(
        "Head", parent=styles["Normal"], fontName="Times-Bold",
        fontSize=15, leading=18, alignment=TA_CENTER, textColor=NAVY,
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"], fontName="Times-Roman",
        fontSize=10, leading=13, alignment=TA_CENTER, textColor=GOLD,
    )
    right_style = ParagraphStyle(
        "Right", parent=styles["Normal"], fontName="Times-Roman",
        fontSize=11, leading=15, alignment=TA_RIGHT,
    )

    story = []
    if os.path.exists(LOGO_PATH):
        try:
            story.append(RLImage(LOGO_PATH, width=58, height=58, hAlign="CENTER"))
            story.append(Spacer(1, 6))
        except Exception:
            pass
    story.append(Paragraph("MEDICAL DOCTOR INTERNATIONAL ACADEMY", head_style))
    story.append(Paragraph("20 Years of Medical Education", sub_style))
    story.append(Spacer(1, 4))
    # Gold rule under the header.
    rule = Table([[""]], colWidths=[doc.width])
    rule.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1.2, GOLD)]))
    story.append(rule)
    story.append(Spacer(1, 16))

    story.append(Paragraph(_fmt_date(issue_date), right_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>LETTER OF RECOMMENDATION</b>", ParagraphStyle(
        "Title2", parent=body_style, fontName="Times-Bold", fontSize=13, alignment=TA_CENTER, spaceAfter=16)))

    for para in _split_paragraphs(body_text):
        story.append(Paragraph(_html_escape(para), body_style))

    story.append(Spacer(1, 26))
    story.append(Paragraph("Sincerely,", body_style))
    story.append(Spacer(1, 26))
    story.append(Paragraph(f"<b>{_html_escape(signatory_name)}</b>", body_style))
    story.append(Paragraph(_html_escape(signatory_title), ParagraphStyle(
        "SigTitle", parent=body_style, spaceAfter=0, fontSize=11)))
    story.append(Paragraph("Medical Doctor International Academy", ParagraphStyle(
        "SigOrg", parent=body_style, fontSize=11, textColor=NAVY)))

    doc.build(story)
    return buf.getvalue()


def _split_paragraphs(text: str):
    text = (text or "").strip()
    if not text:
        return ["This student has successfully completed the Premedical Studies Program."]
    # Split on blank lines; collapse single newlines into spaces within a paragraph.
    paras, cur = [], []
    for line in text.splitlines():
        if line.strip() == "":
            if cur:
                paras.append(" ".join(cur)); cur = []
        else:
            cur.append(line.strip())
    if cur:
        paras.append(" ".join(cur))
    return paras or [text]


def _html_escape(s: str) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ── CLAUDE: DRAFT THE RECOMMENDATION LETTER ───────────────────

def draft_recommendation(student_name: str, course_name: str, gpa,
                         subjects=None, final_grade: str = None, remark: str = None) -> str:
    """Ask Claude to draft a formal recommendation letter body. Returns plain
    text (paragraphs separated by blank lines), with NO date, salutation header,
    or signature block — those are added by the PDF. The teacher reviews/edits
    this before anything is sent. Raises on failure so the caller can report it."""
    import anthropic

    subj = ", ".join(subjects) if subjects else "Biology, Chemistry, Physics, Anatomy & Physiology, and Medical English"
    facts = [
        f"Student name: {student_name}",
        f"Program: {course_name}",
        f"Overall average (GPA) across all assessed exams: {gpa}%" if gpa is not None else "Overall average: not yet finalised",
        f"Core subjects studied: {subj}",
    ]
    if final_grade:
        facts.append(f"Final grade / distinction awarded by the academic team: {final_grade}")
    if remark:
        facts.append(f"Teacher's note about this student: {remark}")
    facts_block = "\n".join(f"- {f}" for f in facts)

    prompt = (
        "You are the Academic Director of the Medical Doctor International Academy, a premedical "
        "preparation program. Write a formal, warm and credible Letter of Recommendation that this "
        "student can submit to medical and dental universities as part of their application.\n\n"
        "Use these facts (do not invent grades, awards, or anecdotes beyond what is given):\n"
        f"{facts_block}\n\n"
        "Requirements:\n"
        "- Begin with a salutation line 'To the Admissions Committee,'.\n"
        "- 3 to 4 short paragraphs, roughly 220-300 words total.\n"
        "- Speak to the student's academic achievement in the premedical program, readiness for "
        "medical studies, and personal qualities (dedication, diligence) supported by the facts.\n"
        "- Professional, sincere tone — not over-the-top.\n"
        "- Refer to the student by their full name first, then 'he/she' is unknown so use the full "
        "name or 'this student' rather than guessing gender.\n"
        "- Do NOT include a date, letterhead, the words 'Sincerely', or any signature block — those "
        "are added separately. Output ONLY the salutation and body paragraphs, separated by blank lines. "
        "Plain text, no markdown."
    )

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    return "\n\n".join(p.strip() for p in parts if p and p.strip()).strip()
