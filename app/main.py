"""
app/main.py
===========
VoxOps Backend — FastAPI application entry point.

HOW IT WORKS:
- We create one FastAPI app instance.
- We register the auth and users routers under /api/v1.
- The root GET / endpoint serves as a health check.

HOW TO RUN:
    uvicorn app.main:app --reload

HOW TO VIEW API DOCS:
    http://127.0.0.1:8000/docs    ← Interactive Swagger UI
    http://127.0.0.1:8000/redoc  ← Alternative docs (ReDoc)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.shared.errors import register_exception_handlers
from app.shared.response import BaseResponse, ERROR_RESPONSES, ok

from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.departments.router import router as departments_router
from app.modules.jobs.router import router as jobs_router


# ── Create the FastAPI App ────────────────────────────────────────────────────
app = FastAPI(
    title="VoxOps Backend API",
    description=(
        "AI Workplace Assistant — Backend API\n\n"
        "## Authentication\n"
        "Most endpoints require a JWT bearer token.\n"
        "1. Use `POST /api/v1/auth/login` with your credentials.\n"
        "2. Copy `data.access_token` from the response.\n"
        "3. Click **Authorize** in Swagger and paste the token.\n\n"
        "## Modules Implemented\n"
        "- **Authentication**: Login, logout, current user, password change\n"
        "- **User Profile**: View and update your profile\n"
        "- **Departments**: Organization department directory\n"
        "- **Jobs**: Field work, assignment, and status\n\n"
        "## Scope Note\n"
        "Service reports, activity, request routing, AI, and Knowledge Base are under development."
    ),
    version="1.0.0",
    contact={
        "name": "VoxOps Team",
        "email": "team@voxops.example.com",
    },
    license_info={
        "name": "Private — Internal Use Only",
    },
)

register_exception_handlers(app)


# ── CORS Middleware ───────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing.
# This allows the frontend (running on a different port/domain) to call the API.
# In production, replace allow_origins=["*"] with your actual frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins (development only!)
    allow_credentials=True,
    allow_methods=["*"],          # Allow all HTTP methods
    allow_headers=["*"],          # Allow all headers
)


# ── Register Routers ──────────────────────────────────────────────────────────
# All routes will be prefixed with /api/v1
# Auth routes:  /api/v1/auth/login, /api/v1/auth/me, etc.
# User routes:  /api/v1/users/me, etc.

app.include_router(auth_router, prefix="/api/v1", responses=ERROR_RESPONSES)
app.include_router(users_router, prefix="/api/v1", responses=ERROR_RESPONSES)
app.include_router(departments_router, prefix="/api/v1", responses=ERROR_RESPONSES)
app.include_router(jobs_router, prefix="/api/v1", responses=ERROR_RESPONSES)


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get(
    "/",
    response_model=BaseResponse[dict],
    response_model_exclude_none=True,
    responses=ERROR_RESPONSES,
    tags=["Health"],
    summary="Health check",
    description="Simple health check endpoint. Returns a confirmation that the server is running.",
)
def root() -> BaseResponse[dict]:
    """GET / — health check"""
    return ok("VoxOps Backend is running", {
        "version": "1.0.0",
        "docs": "http://127.0.0.1:8000/docs",
        "status": "ok",
    })
