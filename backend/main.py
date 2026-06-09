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


# ── ROUTES ───────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MDA LMS Backend"}


@app.post("/admin/create-student")
def create_student(body: CreateStudentRequest, _=Depends(get_superadmin_user)):
    """Create a single student account."""
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

    update_data = {"full_name": body.full_name, "role": "student", "status": "active"}
    if body.expiry_date:
        update_data["expiry_date"] = body.expiry_date

    try:
        supabase.table("profiles").upsert({"id": user_id, **update_data}).execute()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"User was created in auth but profile update failed: {str(e)}"
        )

    return {
        "success": True,
        "user_id": user_id,
        "email": body.email,
        "password": password,
        "full_name": body.full_name
    }


@app.post("/admin/bulk-create-students")
def bulk_create_students(body: BulkCreateRequest, _=Depends(get_superadmin_user)):
    """Bulk create student accounts from a list."""
    created = []
    failed = []

    existing_usernames: set = set()

    for entry in body.students:
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
                "role": "student",
                "status": "active"
            }
            if body.expiry_date:
                update_data["expiry_date"] = body.expiry_date

            supabase.table("profiles").upsert(update_data).execute()

            created.append({
                "full_name": entry.full_name,
                "email": entry.email,
                "password": password,
                "user_id": user_id
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
            "id": user_id, "full_name": body.full_name, "role": role, "status": "active"
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
        from datetime import date
        if date.fromisoformat(p["expiry_date"]) < date.today():
            raise HTTPException(status_code=403, detail="Your account has expired.")

    try:
        result = supabase.storage.from_("materials").create_signed_url(
            body.storage_path, 7200
        )
        return {"success": True, "signed_url": result["signedURL"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate signed URL: {str(e)}")
