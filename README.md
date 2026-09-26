# VoxOps Backend — Authentication, Departments & Jobs

**Current module guide:** [Phase 1: Departments and Jobs](docs/phase-1-jobs-departments.md) explains the frontend relationship, table keys, endpoints, and the order to try them.

> AI Workplace Assistant — Backend API Foundation  
> Modules: Authentication, User Profile, Departments, and Jobs

---

## Quick start on this computer (PowerShell)

Run these commands from `C:\voxops-backend`. PostgreSQL 18 is already running here on `localhost:5432`, and `.venv` already has the project packages installed.

1. Create the database (enter the PostgreSQL `postgres` password when prompted):

   ```powershell
   & 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h localhost -U postgres -d postgres -c 'CREATE DATABASE voxops;'
   ```

   If it says the database already exists, continue to step 2.

2. Create your private configuration file, then edit it:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   ```

   Replace `yourpassword` in `DATABASE_URL` with the PostgreSQL password. Replace `JWT_SECRET` with a random value from:

   ```powershell
   .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
   ```

   Keep `.env` on your computer; it is ignored by Git. If the database password contains `@`, `:`, `/`, or other URL punctuation, URL-encode it in `DATABASE_URL`.

3. Create the tables, add the development user, and start the API:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe seed_dev.py
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

4. Open `http://127.0.0.1:8000/docs`. The development login is `jane@example.com` / `ChangeMe123!`. Stop the server with Ctrl+C.

To run tests without PostgreSQL or `.env`: `.\.venv\Scripts\python.exe -m pytest tests -q`.

### When a teammate pulls the code

Git includes the migration files and `.env.example`, but it does not include your local PostgreSQL database or private `.env`. The simplest development setup is for each teammate to install PostgreSQL locally, create a `voxops` database, copy `.env.example` to `.env` with their own password and JWT secret, install `requirements.txt` into their own `.venv`, and run `alembic upgrade head` followed by `seed_dev.py`. Everyone then has the same schema and sample user, but separate data.

To work with **the same data**, use a team-managed PostgreSQL server reachable by everyone. Each teammate puts that server's connection URL in their own `.env`; do not commit credentials. Run migrations on that shared database once per schema change. Pulling code alone cannot copy database records or connect to a database running only on someone else's `localhost`.

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
- ✅ Department directory and admin management
- ✅ Field Jobs with assignment, filters, and status changes

Service reports, activity, request routing, AI, and Knowledge Base are not implemented yet. See the Phase 1 guide for the Jobs and Departments boundary.

---

## 2. Requirements

Before starting, you need:

| Tool | Version | Check |
|---|---|---|
| Python | 3.11 or higher (3.14 verified) | `python --version` |
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
python -m venv .venv
```

If `python` resolves to the WindowsApps alias and will not start, use your installed Python executable. On this machine it is `C:\Users\Dell\AppData\Local\Python\pythoncore-3.14-64\python.exe`. If `.venv` already exists, skip this step.

### Step 3 — Activate the virtual environment

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

You'll see `(.venv)` at the start of your terminal prompt. If PowerShell blocks activation, use the `.\.venv\Scripts\python.exe -m ...` form shown below instead.

### Step 4 — Install all dependencies

```powershell
python -m pip install -r requirements.txt
python -m pip check
```

This installs the dependency versions verified together on Python 3.14. Use the same virtual environment for installation, tests, migrations, and server startup. If the repo already has both `venv` and `.venv`, choose one; they are separate environments with separate packages. The requirements constrain bcrypt to the version tested with Passlib.

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
python -m alembic upgrade head
```

This creates the `users` table in your PostgreSQL database.

**To undo the last migration:**
```powershell
python -m alembic downgrade -1
```

**To check current migration status:**
```powershell
python -m alembic current
```

---

## 8. Create Test Users & Roles

### Step 9 — Seed the database with role-based test accounts

```powershell
python seed_users.py
# or
python -m app.db.seed
```

This seeds the database idempotently with a sample organization ("Acme Corp") and pre-verified test users across different roles:

| Email | Password | Role | Organization |
|---|---|---|---|
| `superadmin@voxops.com` | `SuperAdmin123!` | `SUPER_ADMIN` | N/A |
| `admin@acme.com` | `AdminPass123!` | `ORG_ADMIN` | Acme Corp |
| `bob@acme.com` | `MemberPass123!` | `EMPLOYEE` | Acme Corp |

> ⚠️ These accounts are set with `is_email_verified = true` and `status = ACTIVE` so you can log in immediately for role-based authorization testing.

---

## 9. Start the Server

### Step 10 — Run FastAPI with auto-reload

```powershell
python -m uvicorn app.main:app --reload
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
| POST | `/api/v1/auth/login` | No | Login, get access & refresh tokens |
| POST | `/api/v1/auth/refresh` | No | Obtain new access token via refresh token |
| GET | `/api/v1/auth/me` | Yes | Get current user |
| POST | `/api/v1/auth/logout` | Yes | Logout (client-side) |
| POST | `/api/v1/auth/change-password` | Yes | Change own password |
| GET | `/api/v1/users/me` | Yes | Get own profile |
| PATCH | `/api/v1/users/me` | Yes | Update own profile |
| GET/POST | `/api/v1/departments` | Yes | List/create departments |
| GET/PUT/DELETE | `/api/v1/departments/{id}` | Yes | Read/update/delete a department |
| GET/POST | `/api/v1/jobs` | Yes | List/create Jobs |
| GET/PUT | `/api/v1/jobs/{id}` | Yes | Read/update a Job by UUID |
| PATCH | `/api/v1/jobs/{id}/status` | Yes | Advance a Job's status |

All responses have `success` and `message`; `data` is present only when needed. See the [Phase 1 guide](docs/phase-1-jobs-departments.md) for permissions, field explanations, and error mapping.

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
5. Copy `data.access_token` from the response

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
python -m pytest tests/ -v
```

Expected output: all tests should show `PASSED`.

The tests use a local SQLite database and test-only configuration (no PostgreSQL or `.env` needed for tests). Running the server, migrations, and seed script still requires `.env` and a running PostgreSQL database.

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
