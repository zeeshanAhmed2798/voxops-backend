"""
app/main.py
===========
VoxOps Backend — FastAPI application entry point.

HOW IT WORKS:
- We create one FastAPI app instance (monolith — single deployable unit).
- We register all module routers under /api/v1.
- CORS is restricted to the production frontend origin + localhost for dev.

HOW TO RUN:
    uvicorn app.main:app --reload

HOW TO VIEW API DOCS:
    http://127.0.0.1:8000/docs    ← Interactive Swagger UI (try every endpoint here)
    http://127.0.0.1:8000/redoc  ← Alternative docs (ReDoc)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from mangum import Mangum

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.knowledge_base.router import router as kb_router


# ── Create the FastAPI App ────────────────────────────────────────────────────
app = FastAPI(
    title="VoxOps Backend API",
    description=(
        "AI Workplace & Field Operations Assistant — Backend API\n\n"
        "## Authentication\n"
        "Most endpoints require a JWT bearer token.\n"
        "1. Register via `POST /api/v1/auth/register` (creates org + admin).\n"
        "2. Or log in via `POST /api/v1/auth/login` with your credentials.\n"
        "3. Copy the `access_token` from the response.\n"
        "4. Click **Authorize** (top right in Swagger) and paste: `Bearer <token>`\n\n"
        "## Modules Implemented\n"
        "- **Authentication**: Register, Login, Refresh, Logout, Me, Change Password\n"
        "- **Password Reset**: Forgot Password, Reset Password\n"
        "- **Member Management**: Admin invite flow (Invite Member, Register Member)\n"
        "- **User Profile**: View and update your profile\n"
        "- **Knowledge Base**: CRUD for org-scoped documents (read=all, write=admin)\n\n"
        "## Multi-Tenancy\n"
        "All data is isolated per organization. Users can only see data from their own org.\n\n"
        "## Role-Based Access Control\n"
        "- **ORG_ADMIN**: Full access including admin-only write operations\n"
        "- **EMPLOYEE / SUPERVISOR / DEPARTMENT_AGENT / FIELD_WORKER**: Read-only for KB\n\n"
        "## Coming Soon\n"
        "Requests, Jobs, Departments, Team, Insights, Reports, Activity modules."
    ),
    version="2.0.0",
    contact={
        "name": "VoxOps Team",
        "email": "team@voxops.example.com",
    },
    license_info={
        "name": "Private — Internal Use Only",
    },
)


# ── CORS Middleware ───────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing.
# We explicitly whitelist the production frontend + localhost for development.
# Never use ["*"] in production — it bypasses cookie/credential security.
_allowed_origins = [
    settings.FRONTEND_ORIGIN,          # Production: https://voxops-web.vercel.app
    "http://localhost:3000",            # Next.js dev server
    "http://127.0.0.1:3000",
    "http://localhost:8000",            # FastAPI Swagger UI (local testing)
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,    # Required for cookies/auth headers
    allow_methods=["*"],       # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],       # Allow all headers (Authorization, Content-Type, etc.)
)


# ── Register Routers ──────────────────────────────────────────────────────────
# All routes are prefixed with /api/v1 for API versioning.
# Adding a new module: create its router and include it here.

app.include_router(auth_router, prefix="/api/v1")           # /api/v1/auth/...
app.include_router(users_router, prefix="/api/v1")          # /api/v1/users/...
app.include_router(kb_router, prefix="/api/v1")             # /api/v1/knowledge-base/...


# ── Health Check Endpoints ────────────────────────────────────────────────────

_health_response = {
    "status": "ok",
    "message": "VoxOps Backend is running",
    "version": "2.0.0",
    "docs": "/docs",
    "modules": [
        "auth",
        "users",
        "knowledge-base",
    ],
}


@app.get(
    "/",
    tags=["Health"],
    summary="Root health check",
    description="Simple health check. Confirms the server is running.",
)
def root() -> dict:
    """GET / — root health check"""
    return _health_response


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Dedicated health check endpoint for load balancers and uptime monitors.",
)
def health() -> dict:
    """GET /health — dedicated health check endpoint"""
    return _health_response


# ── Vercel Serverless Handler ─────────────────────────────────────────────────
# Mangum wraps the ASGI app so Vercel (and AWS Lambda) can invoke it.
# When running locally with uvicorn, this line is simply ignored.
handler = Mangum(app, lifespan="off")
