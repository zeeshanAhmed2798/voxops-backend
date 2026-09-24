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
from app.modules.team_members.router import router as team_members_router


OPENAPI_TAGS = [
    {
        "name": "Teams — Member Directory",
        "description": "Search, invite, inspect, update, and deactivate organization members.",
    },
    {
        "name": "Teams — Application Roles",
        "description": "UUID-backed application roles available in the invite-member form.",
    },
    {
        "name": "Departments — Directory",
        "description": "List, create, edit, delete, and read complete department configuration.",
    },
    {
        "name": "Departments — Categories",
        "description": "Manage the request categories available inside a department.",
    },
    {
        "name": "Departments — Roles",
        "description": "Manage operational routing roles such as IT Support or HR Supervisor.",
    },
    {
        "name": "Departments — Routing",
        "description": "Route each request category to a department role and optional priority.",
    },
    {
        "name": "Departments — Escalation",
        "description": "Manage the unresolved-time threshold and escalation role for a department.",
    },
]


# ── Create the FastAPI App ────────────────────────────────────────────────────
app = FastAPI(
    title="VoxOps Backend API",
    description="""## Modules Implemented
- **Authentication**: Login, logout, current user, password change
- **User Profile**: View and update your profile
- **Departments**: Organization department directory
- **Jobs**: Field work, assignment, and status
""",
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
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
app.include_router(team_members_router, prefix="/api/v1", responses=ERROR_RESPONSES)


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
