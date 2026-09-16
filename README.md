# VoxOps Backend — Authentication & User Profile

> AI Workplace Assistant — Backend API Foundation  
> Module: Authentication + User Profile + Security Foundation

---

## Table of Contents

1. [What This Is](#1-what-this-is)
2. [Requirements](#2-requirements)
3. [Project Structure](#3-project-structure)
4. [Step-by-Step Setup](#4-step-by-step-setup)
5. [Environment Variables](#5-environment-variables)
6. [PostgreSQL Setup](#6-postgresql-setup)
7. [Database Migrations](#7-database-migrations)
8. [Create Test User](#8-create-test-user)
9. [Start the Server](#9-start-the-server)
10. [API Endpoints](#10-api-endpoints)
11. [Testing in Swagger](#11-testing-in-swagger)
12. [Running Automated Tests](#12-running-automated-tests)
13. [Git Workflow](#13-git-workflow)
14. [For Other Team Members](#14-for-other-team-members)

---

## 1. What This Is

This is the **backend foundation** for VoxOps.

It implements:
- ✅ User authentication (login with email + password)
- ✅ JWT (JSON Web Token) security
- ✅ Password hashing (bcrypt — secure)
- ✅ Current-user dependency (reusable by all team modules)
- ✅ Role-based authorization foundation
- ✅ Multi-tenant organization isolation
- ✅ User profile view and update

It does **NOT** implement other modules (Tickets, AI, Knowledge Base, etc.) — those are other team members' responsibility.

---

## 2. Requirements

Before starting, you need:

| Tool | Version | Check |
|---|---|---|
| Python | 3.11 or higher | `python --version` |
| PostgreSQL | 14 or higher | `psql --version` |
| pip | Latest | `pip --version` |
| Git | Any | `git --version` |

---

## 3. Project Structure

```
backend/
├── app/
│   ├── main.py              ← FastAPI app entry point
│   ├── core/
│   │   ├── config.py        ← Reads .env settings
│   │   ├── database.py      ← SQLAlchemy database setup
│   │   └── security.py      ← Password hashing + JWT
│   ├── models/
│   │   └── user.py          ← User database model + enums
│   ├── schemas/
│   │   ├── auth.py          ← Login/token schemas
│   │   └── user.py          ← User profile schemas
│   ├── dependencies/
│   │   └── auth.py          ← get_current_user + require_roles
│   └── modules/
│       ├── auth/            ← Login, /me, logout, change-password
│       └── users/           ← GET/PATCH /users/me
├── alembic/                 ← Database migrations
│   └── versions/
│       └── 001_create_users.py
├── tests/
│   ├── conftest.py          ← Test fixtures
│   └── test_auth.py         ← Automated tests
├── seed_dev.py              ← Create test user (dev only!)
├── alembic.ini              ← Alembic config
├── requirements.txt         ← Python dependencies
├── .env.example             ← Environment template
├── .gitignore               ← Keeps .env out of git
└── README.md                ← You are here
```

---

## 4. Step-by-Step Setup

### Step 1 — Open a terminal and go to the backend directory

```powershell
cd C:\path\to\your\project\backend
```

### Step 2 — Create a Python virtual environment

A virtual environment keeps your project's packages separate from other projects.

```powershell
python -m venv venv
```

### Step 3 — Activate the virtual environment

**Windows (PowerShell):**
```powershell
venv\Scripts\activate
```

You'll see `(venv)` at the start of your terminal prompt — that means it's active.

### Step 4 — Install all dependencies

```powershell
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, Alembic, bcrypt, JWT libraries, etc.

---

## 5. Environment Variables

### Step 5 — Copy the template

```powershell
copy .env.example .env
```

### Step 6 — Edit the .env file

Open `.env` in any text editor and fill in your real values:

```env
DATABASE_URL=postgresql+psycopg://postgres:yourpassword@localhost:5432/voxops
JWT_SECRET=your-long-random-secret-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
APP_ENV=development
DEBUG=true
```

**How to generate a secure JWT_SECRET:**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output and use it as your JWT_SECRET.

> ⚠️ **NEVER commit your .env file to Git.** It contains secrets. The `.gitignore` already excludes it.

---

## 6. PostgreSQL Setup

### Step 7 — Create the database

Open pgAdmin or psql and run:

```sql
CREATE DATABASE voxops;
```

Or from the terminal:
```powershell
psql -U postgres -c "CREATE DATABASE voxops;"
```

Make sure the username and password in your `.env` DATABASE_URL match your PostgreSQL setup.

---

## 7. Database Migrations

Alembic manages your database schema. Think of migrations like a version history for your database tables.

### Step 8 — Apply the migrations (create the users table)

```powershell
alembic upgrade head
```

This creates the `users` table in your PostgreSQL database.

**To undo the last migration:**
```powershell
alembic downgrade -1
```

**To check current migration status:**
```powershell
alembic current
```

---

## 8. Create Test User

### Step 9 — Seed the development database

```powershell
python seed_dev.py
```

This creates a test user you can log in with:

| Field | Value |
|---|---|
| Email | jane@example.com |
| Password | ChangeMe123! |
| Role | ORG_ADMIN |
| Status | ACTIVE |

> ⚠️ This script is for **development only**. Change the password after first login using the change-password API.

---

## 9. Start the Server

### Step 10 — Run FastAPI with auto-reload

```powershell
uvicorn app.main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

The `--reload` flag means the server restarts automatically whenever you edit a file.

---

## 10. API Endpoints

| Method | URL | Auth Required | Description |
|---|---|---|---|
| GET | `/` | No | Health check |
| POST | `/api/v1/auth/login` | No | Login, get JWT token |
| GET | `/api/v1/auth/me` | Yes | Get current user |
| POST | `/api/v1/auth/logout` | Yes | Logout (client-side) |
| POST | `/api/v1/auth/change-password` | Yes | Change own password |
| GET | `/api/v1/users/me` | Yes | Get own profile |
| PATCH | `/api/v1/users/me` | Yes | Update own profile |

---

## 11. Testing in Swagger

### Step 11 — Open Swagger

With the server running, go to:
```
http://127.0.0.1:8000/docs
```

You'll see all endpoints listed interactively.

### Step 12 — Test Login

1. Click `POST /api/v1/auth/login`
2. Click **Try it out**
3. Enter:
```json
{
  "email": "jane@example.com",
  "password": "ChangeMe123!"
}
```
4. Click **Execute**
5. Copy the `access_token` from the response

### Step 13 — Authorize in Swagger

1. Click the **Authorize 🔓** button (top right of Swagger)
2. In the "HTTPBearer" box, paste your token (just the token, not "Bearer")
3. Click **Authorize** → **Close**

Now all protected endpoints will include your token automatically.

### Step 14 — Test Protected Endpoints

- `GET /api/v1/auth/me` → should return your user profile
- `GET /api/v1/users/me` → same profile
- `PATCH /api/v1/users/me` → update your name/job_title/timezone/phone

---

## 12. Running Automated Tests

```powershell
pytest tests/ -v
```

Expected output: all tests should show `PASSED`.

The tests use a local SQLite database (no PostgreSQL needed for tests).

---

## 13. Git Workflow

This feature is developed on the `feature/auth-profile` branch.

```powershell
# Switch to or create the feature branch
git checkout -b feature/auth-profile

# Stage all new files
git add .

# Commit
git commit -m "feat: implement authentication and user profile foundation"

# Push to remote when ready (only when explicitly asked)
# git push origin feature/auth-profile
```

> ❗ Do NOT merge to `main` without team review.

---

## 14. For Other Team Members

### Importing shared utilities

```python
# Get current user in a protected route
from app.dependencies.auth import get_current_user
from app.models.user import User

@router.get("/your-endpoint")
def your_route(current_user: User = Depends(get_current_user)):
    org_id = current_user.organization_id  # Use for isolation!
    ...

# Role-restricted route
from app.dependencies.auth import require_roles
from app.models.user import UserRole

@router.get("/admin-only")
def admin_route(
    current_user: User = Depends(require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN))
):
    ...

# Database session
from app.core.database import get_db
from sqlalchemy.orm import Session

@router.get("/your-data")
def get_data(db: Session = Depends(get_db)):
    ...

# User model and enums
from app.models.user import User, UserRole, UserStatus

# User schemas
from app.schemas.user import UserResponse
```

### Organization Isolation Pattern

Always filter queries by `organization_id` to keep tenants isolated:

```python
# ✅ CORRECT — filters by org
tickets = db.query(Ticket).filter(
    Ticket.organization_id == current_user.organization_id
).all()

# ❌ WRONG — returns ALL orgs' data
tickets = db.query(Ticket).all()
```

---

*VoxOps Backend — Authentication & User Profile Module*  
*Built with FastAPI + SQLAlchemy + PostgreSQL*
