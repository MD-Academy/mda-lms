import os
import secrets
import string
from typing import Optional, List
from datetime import date

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

import emails

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://students.medicaldoctor-studies.com,https://admin.medicaldoctor-studies.com"
).split(",")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(title="MDA LMS Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── GLOBAL ERROR HANDLERS ─────────────────────────────────────
# Ensure EVERY response — including unhandled 500s — carries CORS
# headers, so the browser shows the real error instead of a
# misleading "blocked by CORS policy" message.

def _cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin")
    if origin and origin in ALLOWED_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=_cors_headers(request),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Surface the real error text so it is visible in the browser.
    return JSONResponse(
        status_code=500,
        content={"detail": f"Server error: {type(exc).__name__}: {str(exc)}"},
        headers=_cors_headers(request),
    )


# ── AUTH HELPERS ──────────────────────────────────────────────

def _verify_user(authorization: str, allowed_roles: tuple):
    """Verify the Bearer token and that the user's role is in allowed_roles."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")

    token = authorization.split(" ", 1)[1]

    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired session.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    try:
        profile = supabase.table("profiles").select("role").eq("id", user.id).single().execute()
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Could not verify profile: {str(e)}")

    role = (profile.data or {}).get("role")
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Access denied.")

    return user


def get_admin_user(authorization: str = Header(...)):
    """Admin OR superadmin — content management and shared operations."""
    return _verify_user(authorization, ("admin", "superadmin"))


def get_superadmin_user(authorization: str = Header(...)):
    """Superadmin only — student management and admin/superadmin management."""
    return _verify_user(authorization, ("superadmin",))


# ── PASSWORD / USERNAME GENERATORS ───────────────────────────

def generate_password() -> str:
    chars = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(8))
    return f"MDA-{random_part}"


def generate_username(full_name: str, existing: set) -> str:
    parts = full_name.lower().strip().split()
    if len(parts) >= 2:
        base = f"{parts[0]}.{parts[-1]}"
    else:
        base = parts[0] if parts else "student"

    base = "".join(c for c in base if c.isalnum() or c == ".")

    username = base
    counter = 1
    while username in existing:
        username = f"{base}{counter}"
        counter += 1
    return username


# ── MODELS ───────────────────────────────────────────────────

class CreateStudentRequest(BaseModel):
    full_name: str
    email: str
    password: Optional[str] = None
    expiry_date: Optional[str] = None


class CreateAdminRequest(BaseModel):
    full_name: str
    email: str
    role: Optional[str] = "admin"   # 'admin' (teacher) or 'superadmin'


class BulkStudentEntry(BaseModel):
    full_name: str
    email: str


class BulkCreateRequest(BaseModel):
    students: List[BulkStudentEntry]
    expiry_date: Optional[str] = None


class UpdateStudentRequest(BaseModel):
    full_name: Optional[str] = None
    status: Optional[str] = None
    expiry_date: Optional[str] = None


class SignedUrlRequest(BaseModel):
    storage_path: str


class NotifPrefsRequest(BaseModel):
    notify_announcements: bool
    notify_schedule: bool


class NotifyAnnouncementRequest(BaseModel):
    title: str
    body: str


class NotifyScheduleRequest(BaseModel):
    topic: str
    entry_date: str
    subject_name: Optional[str] = None
    details: Optional[str] = None


# ── ROUTES ───────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MDA LMS Backend"}


@app.post("/admin/create-student")
def create_student(body: CreateStudentRequest, _=Depends(get_superadmin_user)):
    """Create a single student account."""
    if not emails.is_valid_email(body.email):
        raise HTTPException(status_code=400, detail=f"'{body.email}' is not a valid email address.")
    password = body.password or generate_password()

    try:
        result = supabase.auth.admin.create_user({
            "email": body.email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "full_name": body.full_name,
                "role": "student"
            }
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create user: {str(e)}")

    if not result or not getattr(result, "user", None):
        raise HTTPException(status_code=400, detail="User creation returned no user object.")

    user_id = result.user.id

    update_data = {"full_name": body.full_name, "email": body.email, "role": "student", "status": "active"}
    if body.expiry_date:
        update_data["expiry_date"] = body.expiry_date

    try:
        supabase.table("profiles").upsert({"id": user_id, **update_data}).execute()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"User was created in auth but profile update failed: {str(e)}"
        )

    # Welcome email with login details. Never let a mail failure break creation —
    # the admin still gets the credentials in the response to hand over manually.
    subject, html = emails.welcome_email(body.full_name, body.email, password, body.expiry_date)
    email_sent = emails.send_email(body.email, subject, html)

    return {
        "success": True,
        "user_id": user_id,
        "email": body.email,
        "password": password,
        "full_name": body.full_name,
        "email_sent": email_sent
    }


@app.post("/admin/bulk-create-students")
def bulk_create_students(body: BulkCreateRequest, _=Depends(get_superadmin_user)):
    """Bulk create student accounts from a list."""
    created = []
    failed = []

    existing_usernames: set = set()

    for entry in body.students:
        if not emails.is_valid_email(entry.email):
            failed.append({
                "full_name": entry.full_name,
                "email": entry.email,
                "error": "Invalid email address"
            })
            continue

        password = generate_password()
        username = generate_username(entry.full_name, existing_usernames)
        existing_usernames.add(username)

        try:
            result = supabase.auth.admin.create_user({
                "email": entry.email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": entry.full_name,
                    "role": "student"
                }
            })

            user_id = result.user.id
            update_data = {
                "id": user_id,
                "full_name": entry.full_name,
                "email": entry.email,
                "role": "student",
                "status": "active"
            }
            if body.expiry_date:
                update_data["expiry_date"] = body.expiry_date

            supabase.table("profiles").upsert(update_data).execute()

            subject, html = emails.welcome_email(entry.full_name, entry.email, password, body.expiry_date)
            email_sent = emails.send_email(entry.email, subject, html)

            created.append({
                "full_name": entry.full_name,
                "email": entry.email,
                "password": password,
                "user_id": user_id,
                "email_sent": email_sent
            })

        except Exception as e:
            failed.append({
                "full_name": entry.full_name,
                "email": entry.email,
                "error": str(e)
            })

    return {
        "success": True,
        "created_count": len(created),
        "failed_count": len(failed),
        "created": created,
        "failed": failed
    }


@app.patch("/admin/update-student/{user_id}")
def update_student(user_id: str, body: UpdateStudentRequest, _=Depends(get_superadmin_user)):
    """Update student profile — name, status, expiry date."""
    update_data = {}
    if body.full_name is not None:
        update_data["full_name"] = body.full_name
    if body.status is not None:
        if body.status not in ("active", "suspended"):
            raise HTTPException(status_code=400, detail="Status must be 'active' or 'suspended'.")
        update_data["status"] = body.status
    if body.expiry_date is not None:
        update_data["expiry_date"] = body.expiry_date if body.expiry_date != "" else None

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update.")

    supabase.table("profiles").update(update_data).eq("id", user_id).execute()
    return {"success": True, "updated": update_data}


@app.delete("/admin/delete-student/{user_id}")
def delete_student(user_id: str, _=Depends(get_superadmin_user)):
    """Permanently delete a student account."""
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete user: {str(e)}")
    return {"success": True, "deleted_user_id": user_id}


@app.post("/admin/reset-password/{user_id}")
def reset_password(user_id: str, _=Depends(get_superadmin_user)):
    """Generate a new password for a student and return it to the admin."""
    new_password = generate_password()
    try:
        supabase.auth.admin.update_user_by_id(user_id, {"password": new_password})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to reset password: {str(e)}")
    return {"success": True, "new_password": new_password}


# ── EMAIL NOTIFICATIONS (Phase 2) ────────────────────────────

def _active_subscribed_students(pref_column: str):
    """Active, non-expired students who opted in to `pref_column`, with a valid email."""
    today = date.today().isoformat()
    rows = (supabase.table("profiles")
            .select("full_name, email, status, expiry_date")
            .eq("role", "student").eq("status", "active").eq(pref_column, True)
            .execute().data or [])
    out = []
    for r in rows:
        exp = r.get("expiry_date")
        if exp and exp < today:
            continue  # expired → suppress
        if r.get("email"):
            out.append(r)
    return out


@app.post("/student/notification-prefs")
def set_notification_prefs(body: NotifPrefsRequest, authorization: str = Header(...)):
    """A student updates their own email-notification toggles."""
    user = _require_active_student(authorization)
    supabase.table("profiles").update({
        "notify_announcements": body.notify_announcements,
        "notify_schedule": body.notify_schedule,
    }).eq("id", user.id).execute()
    return {"success": True}


@app.post("/admin/notify/announcement")
def notify_announcement(body: NotifyAnnouncementRequest, _=Depends(get_admin_user)):
    """Email subscribed students that a new announcement was posted."""
    students = _active_subscribed_students("notify_announcements")
    messages = []
    for s in students:
        subject, html = emails.announcement_email(s.get("full_name"), body.title, body.body)
        messages.append({"to": s["email"], "subject": subject, "html": html})
    sent = emails.send_batch(messages)
    return {"success": True, "recipients": len(students), "sent": sent}


@app.post("/admin/notify/schedule")
def notify_schedule(body: NotifyScheduleRequest, _=Depends(get_admin_user)):
    """Email subscribed students that a new session was scheduled."""
    students = _active_subscribed_students("notify_schedule")
    messages = []
    for s in students:
        subject, html = emails.schedule_email(s.get("full_name"), body.topic, body.entry_date,
                                               body.subject_name, body.details)
        messages.append({"to": s["email"], "subject": subject, "html": html})
    sent = emails.send_batch(messages)
    return {"success": True, "recipients": len(students), "sent": sent}


# ── ADMIN / SUPERADMIN MANAGEMENT (superadmin only) ──────────

@app.post("/admin/create-admin")
def create_admin(body: CreateAdminRequest, _=Depends(get_superadmin_user)):
    """Create an admin (teacher) or superadmin account. Superadmin only."""
    role = body.role if body.role in ("admin", "superadmin") else "admin"
    password = generate_password()

    try:
        result = supabase.auth.admin.create_user({
            "email": body.email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": body.full_name, "role": role}
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create user: {str(e)}")

    if not result or not getattr(result, "user", None):
        raise HTTPException(status_code=400, detail="User creation returned no user object.")

    user_id = result.user.id
    try:
        supabase.table("profiles").upsert({
            "id": user_id, "full_name": body.full_name, "email": body.email, "role": role, "status": "active"
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"User created but profile update failed: {str(e)}")

    return {
        "success": True,
        "user_id": user_id,
        "email": body.email,
        "password": password,
        "full_name": body.full_name,
        "role": role
    }


@app.delete("/admin/delete-admin/{user_id}")
def delete_admin(user_id: str, _=Depends(get_superadmin_user)):
    """Delete an admin/superadmin account. Superadmin only."""
    try:
        supabase.auth.admin.delete_user(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete user: {str(e)}")
    return {"success": True, "deleted_user_id": user_id}


@app.post("/admin/clear-mfa/{user_id}")
def clear_mfa(user_id: str, _=Depends(get_superadmin_user)):
    """Remove all 2FA factors for a user (lockout recovery). Superadmin only."""
    try:
        res = supabase.auth.admin.mfa.list_factors({"user_id": user_id})
        factors = getattr(res, "factors", None)
        if factors is None and isinstance(res, dict):
            factors = res.get("factors", [])
        factors = factors or []
        removed = 0
        for f in factors:
            fid = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else None)
            if fid:
                supabase.auth.admin.mfa.delete_factor({"user_id": user_id, "id": fid})
                removed += 1
        return {"success": True, "removed": removed}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not reset 2FA: {str(e)}")


@app.post("/materials/signed-url")
def get_signed_url(body: SignedUrlRequest, _=Depends(get_admin_user)):
    """Generate a short-lived signed URL for a private material file."""
    try:
        result = supabase.storage.from_("materials").create_signed_url(
            body.storage_path, 7200
        )
        return {"success": True, "signed_url": result["signedURL"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate signed URL: {str(e)}")


@app.post("/materials/signed-url/student")
def get_signed_url_student(body: SignedUrlRequest, authorization: str = Header(...)):
    """Generate a signed URL for a student to access a material."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")

    token = authorization.split(" ", 1)[1]

    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session.")

    profile = supabase.table("profiles").select("status, expiry_date, role").eq("id", user.id).single().execute()
    p = profile.data
    if not p:
        raise HTTPException(status_code=403, detail="Account not found.")
    if p["status"] == "suspended":
        raise HTTPException(status_code=403, detail="Your account has been suspended.")
    if p["expiry_date"]:
        if date.fromisoformat(p["expiry_date"]) < date.today():
            raise HTTPException(status_code=403, detail="Your account has expired.")

    # Verify the student is actually allowed to open THIS file (visible + enrolled),
    # so they can't fetch arbitrary or hidden files by guessing a path.
    today_iso = date.today().isoformat()
    allowed = False

    mat = supabase.table("materials").select("room_id, is_visible").eq("storage_path", body.storage_path).limit(1).execute()
    if mat.data:
        m = mat.data[0]
        if m.get("is_visible"):
            enr = supabase.table("course_enrollments").select("course_id").eq("student_id", user.id).execute()
            course_ids = [r["course_id"] for r in (enr.data or [])]
            if course_ids:
                cs = supabase.table("course_subjects").select("course_id").eq("room_id", m["room_id"]).in_("course_id", course_ids).execute()
                cand = [r["course_id"] for r in (cs.data or [])]
                if cand:
                    crs = supabase.table("courses").select("is_visible, expires_at").in_("id", cand).execute()
                    for c in (crs.data or []):
                        if c.get("is_visible") and (not c.get("expires_at") or c["expires_at"] >= today_iso):
                            allowed = True
                            break
    else:
        bk = supabase.table("booklets").select("is_visible").eq("storage_path", body.storage_path).limit(1).execute()
        if bk.data and bk.data[0].get("is_visible"):
            allowed = True  # booklets are available to all active students
        else:
            exm = supabase.table("exams").select("id, is_visible").eq("storage_path", body.storage_path).limit(1).execute()
            if exm.data and exm.data[0].get("is_visible"):
                try:
                    _verify_exam_access(user.id, exm.data[0]["id"])
                    allowed = True
                except HTTPException:
                    allowed = False

    if not allowed:
        raise HTTPException(status_code=403, detail="You don't have access to this file.")

    try:
        result = supabase.storage.from_("materials").create_signed_url(
            body.storage_path, 7200
        )
        return {"success": True, "signed_url": result["signedURL"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate signed URL: {str(e)}")


# ── STUDENT EXAM TAKING (server-side grading; answers never sent to client) ──

class ExamQReq(BaseModel):
    exam_id: str

class ExamSubmitReq(BaseModel):
    exam_id: str
    answers: dict   # { question_id: selected_option_index }


def _require_active_student(authorization: str):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    token = authorization.split(" ", 1)[1]
    try:
        user = supabase.auth.get_user(token).user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session.")
    p = supabase.table("profiles").select("role, status, expiry_date").eq("id", user.id).single().execute().data
    if not p or p.get("role") != "student":
        raise HTTPException(status_code=403, detail="Students only.")
    if p.get("status") == "suspended":
        raise HTTPException(status_code=403, detail="Your account has been suspended.")
    if p.get("expiry_date") and date.fromisoformat(p["expiry_date"]) < date.today():
        raise HTTPException(status_code=403, detail="Your account has expired.")
    return user


def _verify_exam_access(user_id: str, exam_id: str):
    ex = supabase.table("exams").select("id, title, description, type, pass_threshold, time_limit_minutes, is_visible").eq("id", exam_id).limit(1).execute().data
    if not ex or not ex[0].get("is_visible"):
        raise HTTPException(status_code=403, detail="This exam isn't available.")
    e = ex[0]
    enr = supabase.table("course_enrollments").select("course_id").eq("student_id", user_id).execute().data
    course_ids = [r["course_id"] for r in (enr or [])]
    if not course_ids:
        raise HTTPException(status_code=403, detail="You don't have access to this exam.")
    ec = supabase.table("exam_courses").select("course_id").eq("exam_id", exam_id).in_("course_id", course_ids).execute().data
    cand = [r["course_id"] for r in (ec or [])]
    if not cand:
        raise HTTPException(status_code=403, detail="You don't have access to this exam.")
    today_iso = date.today().isoformat()
    crs = supabase.table("courses").select("is_visible, expires_at").in_("id", cand).execute().data
    if not any(c.get("is_visible") and (not c.get("expires_at") or c["expires_at"] >= today_iso) for c in (crs or [])):
        raise HTTPException(status_code=403, detail="You don't have access to this exam.")
    return e


@app.post("/student/exam-questions")
def student_exam_questions(body: ExamQReq, authorization: str = Header(...)):
    user = _require_active_student(authorization)
    e = _verify_exam_access(user.id, body.exam_id)
    qs = supabase.table("exam_questions").select("id, question_text, options_json, order_index").eq("exam_id", body.exam_id).order("order_index").execute().data or []
    prev = supabase.table("exam_attempts").select("score, passed").eq("exam_id", body.exam_id).eq("student_id", user.id).limit(1).execute().data
    return {
        "exam": {"id": e["id"], "title": e["title"], "description": e.get("description"),
                 "pass_threshold": e["pass_threshold"], "time_limit_minutes": e.get("time_limit_minutes")},
        "questions": qs,
        "previous": prev[0] if prev else None
    }


@app.post("/student/exam-submit")
def student_exam_submit(body: ExamSubmitReq, authorization: str = Header(...)):
    from datetime import datetime
    user = _require_active_student(authorization)
    e = _verify_exam_access(user.id, body.exam_id)
    qs = supabase.table("exam_questions").select("id, correct_answer_index, order_index").eq("exam_id", body.exam_id).order("order_index").execute().data or []
    if not qs:
        raise HTTPException(status_code=400, detail="This exam has no questions yet.")

    total = len(qs)
    correct = 0
    wrong = []
    for i, q in enumerate(qs, start=1):
        ans = body.answers.get(q["id"])
        try:
            if ans is not None and int(ans) == q["correct_answer_index"]:
                correct += 1
            else:
                wrong.append(i)
        except (ValueError, TypeError):
            wrong.append(i)

    score = round(correct / total * 100)
    passed = score >= e["pass_threshold"]
    row = {
        "score": score, "passed": passed,
        "answers_json": body.answers, "wrong_questions": wrong,
        "completed_at": datetime.utcnow().isoformat()
    }
    existing = supabase.table("exam_attempts").select("id").eq("exam_id", body.exam_id).eq("student_id", user.id).limit(1).execute().data
    if existing:
        supabase.table("exam_attempts").update(row).eq("id", existing[0]["id"]).execute()
    else:
        supabase.table("exam_attempts").insert({**row, "exam_id": body.exam_id, "student_id": user.id}).execute()

    return {"score": score, "passed": passed, "total": total, "correct": correct,
            "wrong": wrong, "pass_threshold": e["pass_threshold"]}


# ── STUDENT PER-LESSON QUIZZES (10/10 to pass, with cooldown) ──

class QuizQReq(BaseModel):
    quiz_id: str

class QuizSubmitReq(BaseModel):
    quiz_id: str
    answers: dict


def _verify_quiz_access(user_id: str, quiz_id: str):
    qz = supabase.table("quizzes").select("id, lesson_id, time_limit_minutes, cooldown_minutes, is_visible").eq("id", quiz_id).limit(1).execute().data
    if not qz or not qz[0].get("is_visible"):
        raise HTTPException(status_code=403, detail="This quiz isn't available.")
    q = qz[0]
    les = supabase.table("lessons").select("room_id, is_visible").eq("id", q["lesson_id"]).limit(1).execute().data
    if not les or not les[0].get("is_visible"):
        raise HTTPException(status_code=403, detail="This quiz isn't available.")
    room_id = les[0]["room_id"]
    rm = supabase.table("rooms").select("is_visible").eq("id", room_id).limit(1).execute().data
    if not rm or not rm[0].get("is_visible"):
        raise HTTPException(status_code=403, detail="This quiz isn't available.")
    enr = supabase.table("course_enrollments").select("course_id").eq("student_id", user_id).execute().data
    course_ids = [r["course_id"] for r in (enr or [])]
    if not course_ids:
        raise HTTPException(status_code=403, detail="You don't have access to this quiz.")
    cs = supabase.table("course_subjects").select("course_id").eq("room_id", room_id).in_("course_id", course_ids).execute().data
    cand = [r["course_id"] for r in (cs or [])]
    if not cand:
        raise HTTPException(status_code=403, detail="You don't have access to this quiz.")
    today_iso = date.today().isoformat()
    crs = supabase.table("courses").select("is_visible, expires_at").in_("id", cand).execute().data
    if not any(c.get("is_visible") and (not c.get("expires_at") or c["expires_at"] >= today_iso) for c in (crs or [])):
        raise HTTPException(status_code=403, detail="You don't have access to this quiz.")
    return q


def _cooldown_remaining(user_id: str, quiz_id: str, cooldown_minutes: int):
    from datetime import datetime, timezone
    if not cooldown_minutes:
        return 0
    last = supabase.table("quiz_attempts").select("completed_at").eq("quiz_id", quiz_id).eq("student_id", user_id).not_.is_("completed_at", "null").order("completed_at", desc=True).limit(1).execute().data
    if not last or not last[0].get("completed_at"):
        return 0
    ts = last[0]["completed_at"].replace("Z", "+00:00")
    try:
        last_dt = datetime.fromisoformat(ts)
    except Exception:
        return 0
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
    remaining = cooldown_minutes * 60 - elapsed
    return int(remaining) if remaining > 0 else 0


@app.post("/student/quiz-questions")
def student_quiz_questions(body: QuizQReq, authorization: str = Header(...)):
    user = _require_active_student(authorization)
    q = _verify_quiz_access(user.id, body.quiz_id)
    qs = supabase.table("quiz_questions").select("id, question_text, options_json, order_index").eq("quiz_id", body.quiz_id).order("order_index").execute().data or []
    return {
        "quiz": {"id": q["id"], "time_limit_minutes": q.get("time_limit_minutes"), "cooldown_minutes": q.get("cooldown_minutes")},
        "questions": qs,
        "cooldown_remaining": _cooldown_remaining(user.id, body.quiz_id, q.get("cooldown_minutes") or 0)
    }


@app.post("/student/quiz-submit")
def student_quiz_submit(body: QuizSubmitReq, authorization: str = Header(...)):
    from datetime import datetime, timezone
    user = _require_active_student(authorization)
    q = _verify_quiz_access(user.id, body.quiz_id)

    remaining = _cooldown_remaining(user.id, body.quiz_id, q.get("cooldown_minutes") or 0)
    if remaining > 0:
        raise HTTPException(status_code=403, detail=f"Please wait {remaining // 60}m {remaining % 60}s before retaking this quiz.")

    qs = supabase.table("quiz_questions").select("id, correct_answer_index, order_index").eq("quiz_id", body.quiz_id).order("order_index").execute().data or []
    if not qs:
        raise HTTPException(status_code=400, detail="This quiz has no questions yet.")

    total = len(qs)
    correct = 0
    wrong = []
    for i, qq in enumerate(qs, start=1):
        ans = body.answers.get(qq["id"])
        try:
            if ans is not None and int(ans) == qq["correct_answer_index"]:
                correct += 1
            else:
                wrong.append(i)
        except (ValueError, TypeError):
            wrong.append(i)

    score = round(correct / total * 100)
    passed = (correct == total)   # 10/10 rule: every question must be correct
    supabase.table("quiz_attempts").insert({
        "student_id": user.id, "quiz_id": body.quiz_id,
        "score": score, "answers_json": body.answers,
        "completed_at": datetime.now(timezone.utc).isoformat()
    }).execute()

    return {"score": score, "passed": passed, "total": total, "correct": correct, "wrong": wrong}
