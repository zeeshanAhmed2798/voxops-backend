# VoxOps Backend API

**AI Workplace & Field Operations Assistant — FastAPI Monolith**

> Production-ready multi-tenant B2B backend with JWT authentication, role-based access control, and a full Knowledge Base module.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115 |
| Database | PostgreSQL (psycopg3) |
| ORM | SQLAlchemy 2.0 (sync) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Deployment | Uvicorn + Mangum (Vercel/Lambda) |

---

## Project Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── config.py       # Settings via pydantic-settings (.env loading)
│   │   ├── database.py     # SQLAlchemy engine, session, Base
│   │   ├── security.py     # Password hashing, JWT creation, token helpers
│   │   └── types.py        # GUID type for cross-DB UUID compatibility
│   ├── dependencies/
│   │   └── auth.py         # get_current_user, require_roles, require_admin, get_current_org
│   ├── models/
│   │   ├── organization.py         # Organization table
│   │   ├── user.py                 # User table (with UserRole, UserStatus enums)
│   │   ├── refresh_token.py        # Active sessions (refresh tokens)
│   │   ├── password_reset_token.py # One-time password reset tokens
│   │   ├── invite_token.py         # Admin invite tokens for new members
│   │   └── knowledge_base.py       # Knowledge Base documents
│   ├── schemas/
│   │   ├── auth.py          # Register, Login, Refresh, Invite, Reset schemas
│   │   ├── user.py          # UserResponse, UpdateProfileRequest
│   │   ├── organization.py  # OrganizationResponse
│   │   └── knowledge_base.py # KBDocumentCreate/Update/Response
│   ├── modules/
│   │   ├── auth/
│   │   │   ├── router.py    # All 10 auth endpoints
│   │   │   └── service.py   # Auth business logic
│   │   ├── users/
│   │   │   ├── router.py    # GET/PATCH /users/me
│   │   │   └── service.py   # Profile logic
│   │   └── knowledge_base/
│   │       ├── router.py    # 5 KB endpoints
│   │       └── service.py   # KB business logic with org scoping
│   └── main.py              # App factory, CORS, router registration
├── alembic/
│   ├── versions/
│   │   ├── 001_create_users.py
│   │   ├── 002_create_organizations.py
│   │   ├── 003_add_org_fk_and_is_email_verified.py
│   │   ├── 004_create_refresh_tokens.py
│   │   ├── 005_create_password_reset_tokens.py
│   │   ├── 006_create_invite_tokens.py
│   │   └── 007_create_knowledge_base_documents.py
│   └── env.py
├── .env                     # Local dev env vars (not committed)
├── .env.example             # Template for env vars
├── requirements.txt
├── seed_dev.py              # Demo data seeder
└── alembic.ini
```

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- A virtual environment (recommended)

---

## Local Setup

### 1. Clone and create virtual environment

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your PostgreSQL credentials:

```env
DATABASE_URL=postgresql+psycopg://postgres:yourpassword@localhost:5432/voxops
JWT_SECRET=your-long-random-secret-at-least-64-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
FRONTEND_ORIGIN=https://voxops-web.vercel.app
APP_ENV=development
DEBUG=true
```

**Generate a strong JWT secret:**
```bash
python -c "import secrets; print(secrets.token_hex(64))"
```

### 4. Create the PostgreSQL database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE voxops;
\q
```

### 5. Run migrations

```bash
alembic upgrade head
```

This applies all 7 migrations in order, creating all tables.

### 6. (Optional) Seed demo data

```bash
python seed_dev.py
```

Creates demo org, admin user, member user, and a sample KB document.

**Demo credentials:**
- Admin: `admin@acme.com` / `AdminPass123!`
- Member: `bob@acme.com` / `MemberPass123!`

### 7. Start the development server

```bash
uvicorn app.main:app --reload
```

The API runs at: **http://127.0.0.1:8000**

---

## API Documentation

Once the server is running:

- **Swagger UI**: http://127.0.0.1:8000/docs — interactive, try every endpoint
- **ReDoc**: http://127.0.0.1:8000/redoc — clean reference docs
- **Health Check**: http://127.0.0.1:8000/health

---

## API Endpoints

### Health

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/` | None | Root health check |
| GET | `/health` | None | Dedicated health check |

### Authentication (`/api/v1/auth/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| POST | `/auth/register` | None | — | Register new org + admin (first-time setup) |
| POST | `/auth/login` | None | — | Login → access + refresh token pair |
| POST | `/auth/refresh` | None | — | Get new access token from refresh token |
| POST | `/auth/logout` | ✅ JWT | Any | Invalidate refresh token (true revocation) |
| GET | `/auth/me` | ✅ JWT | Any | Get current user profile |
| POST | `/auth/change-password` | ✅ JWT | Any | Change own password |
| POST | `/auth/forgot-password` | None | — | Request password reset token |
| POST | `/auth/reset-password` | None | — | Set new password using reset token |
| POST | `/auth/invite-member` | ✅ JWT | **ADMIN** | Generate invite token for a new member |
| POST | `/auth/register-member` | None | — | Join org using invite token |

### User Profile (`/api/v1/users/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/users/me` | ✅ JWT | Any | Get own profile |
| PATCH | `/users/me` | ✅ JWT | Any | Update own profile (name, phone, etc.) |

### Knowledge Base (`/api/v1/knowledge-base/`)

| Method | Endpoint | Auth | Role | Description |
|--------|----------|------|------|-------------|
| GET | `/knowledge-base` | ✅ JWT | Any member | List documents (admins see drafts too) |
| GET | `/knowledge-base/{id}` | ✅ JWT | Any member | View full document content |
| POST | `/knowledge-base` | ✅ JWT | **ADMIN** | Create a document |
| PUT | `/knowledge-base/{id}` | ✅ JWT | **ADMIN** | Update a document |
| DELETE | `/knowledge-base/{id}` | ✅ JWT | **ADMIN** | Delete a document |

---

## Authentication Flow

### 1. Register (new organization)
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "org_name": "Acme Corporation",
  "full_name": "Jane Doe",
  "email": "jane@acme.com",
  "password": "SecurePass123"
}
```

Returns `access_token` + `refresh_token`. Store the refresh token securely.

### 2. Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "jane@acme.com",
  "password": "SecurePass123"
}
```

### 3. Use access token
```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

### 4. Refresh when expired
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "<your_refresh_token>"
}
```

Returns a new `access_token` + rotated `refresh_token`.

### 5. Logout
```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh_token": "<your_refresh_token>"
}
```

The refresh token is deleted from the DB — future refresh requests with this token will fail.

---

## Invite Member Flow

### Admin invites someone
```http
POST /api/v1/auth/invite-member
Authorization: Bearer <admin_access_token>
Content-Type: application/json

{
  "email": "newemployee@acme.com",
  "full_name": "John Smith",
  "role": "EMPLOYEE"
}
```

Returns an `invite_token` (also logged to server console). In production, this token would be emailed.

### Invitee registers
```http
POST /api/v1/auth/register-member
Content-Type: application/json

{
  "invite_token": "<invite_token_from_admin>",
  "full_name": "John Smith",
  "password": "MyPassword456"
}
```

Returns `access_token` + `refresh_token` — immediately logged in.

---

## Password Reset Flow

### Step 1: Request reset
```http
POST /api/v1/auth/forgot-password
Content-Type: application/json

{
  "email": "jane@acme.com"
}
```

In dev mode (`APP_ENV=development`), the `reset_token` is returned in the response.
In production, it would be emailed. The token is also printed to the server console.

### Step 2: Set new password
```http
POST /api/v1/auth/reset-password
Content-Type: application/json

{
  "token": "<reset_token>",
  "new_password": "NewSecurePass789"
}
```

---

## Role-Based Access Control (RBAC)

### Roles (from most to least privileged)

| Role | Description |
|------|-------------|
| `SUPER_ADMIN` | Platform-wide access (internal use) |
| `ORG_ADMIN` | Full access within their organization |
| `SUPERVISOR` | Manages teams within an org |
| `DEPARTMENT_AGENT` | Agent in a department |
| `FIELD_WORKER` | Field-based employee |
| `EMPLOYEE` | Standard member (read-only for KB) |

### FastAPI Dependency Usage

```python
from app.dependencies.auth import get_current_user, require_admin, require_roles, get_current_org
from app.models.user import UserRole

# Any logged-in user
@router.get("/profile")
def my_profile(user: User = Depends(get_current_user)):
    ...

# Admin-only shortcut
@router.post("/admin-action")
def admin_action(user: User = Depends(require_admin)):
    ...

# Fine-grained role control
@router.get("/supervisor-area")
def supervisor_area(user: User = Depends(require_roles(UserRole.SUPERVISOR, UserRole.ORG_ADMIN))):
    ...

# Auto-fetch the user's Organization
@router.get("/org-info")
def org_info(org: Organization = Depends(get_current_org)):
    ...
```

---

## Error Codes

| HTTP Status | Meaning |
|-------------|---------|
| 400 | Bad request — invalid token, wrong current password, etc. |
| 401 | Unauthorized — missing, invalid, or expired JWT |
| 403 | Forbidden — insufficient role (e.g. member trying to create KB doc) |
| 404 | Not found — resource doesn't exist in the user's organization |
| 409 | Conflict — email already registered, slug already taken |
| 422 | Validation error — missing field, invalid format, weak password |

---

## Multi-Tenancy Architecture

Every table that contains tenant-specific data has an `organization_id` column with a FK to `organizations.id`. The application layer **always** filters queries by `current_user.organization_id` — users from one organization can never see data from another.

**Tables and their tenant scope:**

| Table | Org-scoped? | Note |
|-------|------------|------|
| `organizations` | Root entity | — |
| `users` | ✅ `organization_id` | SUPER_ADMIN may have NULL |
| `refresh_tokens` | Via `user_id` | Cascades on user delete |
| `password_reset_tokens` | Via `user_id` | Cascades on user delete |
| `invite_tokens` | ✅ `organization_id` | Cascades on org delete |
| `knowledge_base_documents` | ✅ `organization_id` | Cascades on org delete |

---

## Adding a New Module

1. Create `app/models/your_model.py` with `organization_id` FK
2. Import it in `app/models/__init__.py` and `alembic/env.py`
3. Run `alembic revision --autogenerate -m "add your_model"` then `alembic upgrade head`
4. Create `app/schemas/your_module.py` (Create/Update/Response schemas)
5. Create `app/modules/your_module/service.py` (always filter by `organization_id`)
6. Create `app/modules/your_module/router.py` (use `get_current_user`/`require_admin`)
7. Register the router in `app/main.py`

---

## Planned Modules

- **Requests** — Employee service requests and ticketing
- **Jobs** — Field operations job management
- **Departments** — Org structure and department management
- **Team** — Team member management
- **Insights** — Analytics and reporting
- **Activity** — Audit log and activity feed
