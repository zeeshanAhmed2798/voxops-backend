# Phase 1: Departments and Jobs

## What the frontend shows

The [VoxOps design](https://voxops-web.vercel.app/) describes a **Job** as field work or maintenance assigned to a technician. Its list has `All`, `Assigned`, `In Progress`, `Completed`, and `Escalated` filters. A card shows a job number, title, customer/site, city, technician, priority, and status. The detail page adds equipment, a service report, related knowledge, and an activity timeline.

The **Departments** page lists HR, IT, Finance, Operations, and Maintenance. Its subtitle describes request routing. The Manage screen shows categories, escalation, and routing rules. Several buttons in this design currently show sample data without a working create/edit form; it is a UI reference, not an API contract.

### Relationship decision

The design does not explicitly show a Job's department. For the backend, **each Job belongs to exactly one Department**. For example, an AC repair belongs to Maintenance; a network setup can belong to IT. One Department has many Jobs. HR/Finance can exist without field Jobs. Jobs and employee Requests remain separate concepts; a future request may optionally create a Job, but Phase 1 has no Request → Job link.

## Tables and keys

| Table | Primary key | Foreign keys | Purpose |
|---|---|---|---|
| `organizations` | `id` UUID | — | Minimal organization anchor; created because users already carry an organization ID. |
| `departments` | `id` UUID | `organization_id → organizations.id` | Name and description, unique name within one organization. |
| `jobs` | `id` UUID | `organization_id → organizations.id`; `department_id → departments.id`; `assigned_to_id → users.id` | Field job and its assignment. All stored and API identifiers are UUIDs. |
| `users` (existing) | `id` UUID | Existing `organization_id`/`department_id` are UUID fields without FK constraints yet. | Login, role, and potential technician. |

The API checks that a Job's department and technician belong to the signed-in user's organization. Every read and write is scoped by `current_user.organization_id`; clients cannot choose an organization ID in a request body. Existing user organization IDs are copied into the new organizations table during migration. `seed_dev.py` creates the CoolTech organization if needed.

The design shows labels such as `JOB #1042`. That is a **display number**, separate from a UUID primary key. Phase 1 returns only the UUID; add a separate organization-scoped display number when the frontend needs numbered labels.

### Why each new model field exists

| Model | Field | Reason |
|---|---|---|
| Organization | `id` | Stable UUID matching existing `users.organization_id`. |
| Organization | `name` | Workspace name for people to recognize. |
| Organization | `created_at`, `updated_at` | Audit when the workspace was created or changed. |
| Department | `id` | Stable UUID for API links and foreign keys. |
| Department | `organization_id` | Ownership and organization isolation. |
| Department | `name` | Label in the department directory; unique per organization. |
| Department | `description` | Optional explanation of the work handled. |
| Department | `created_at`, `updated_at` | Audit creation and edits. |
| Job | `id` | Stable UUID, never dependent on row order. |
| Job | `organization_id` | Ownership and fast organization-scoped listing. |
| Job | `department_id` | Team responsible for the work. |
| Job | `assigned_to_id` | Required technician; a new Job starts in `ASSIGNED`. |
| Job | `title`, `description` | Short card label and optional detailed instructions. |
| Job | `customer`, `location` | Site and place shown to the technician. |
| Job | `equipment` | Optional item or model being serviced. |
| Job | `priority`, `status` | Urgency badge and workflow tabs. |
| Job | `created_at`, `updated_at` | Chronological ordering and audit of changes. |

The same reasons are recorded as comments beside every field in the SQLAlchemy models. `GUID` stores UUIDs natively in PostgreSQL and as text in SQLite tests.

## Endpoints

All paths start with `/api/v1`. Protected calls need `Authorization: Bearer <access_token>`.

| Method | Path | Who | What it does |
|---|---|---|---|
| GET | `/departments` | Signed-in member | List their organization's departments. |
| POST | `/departments` | Org admin | Add a department. |
| GET | `/departments/{id}` | Signed-in member | Read one department. |
| PUT | `/departments/{id}` | Org admin | Replace its name and description. |
| DELETE | `/departments/{id}` | Org admin | Delete only if no Jobs or users reference it. |
| GET | `/jobs` | Signed-in member | List their organization's Jobs. Optional `status`, `department_id`, `assigned_to_me` filters. |
| POST | `/jobs` | Org admin or supervisor | Create and assign a Job. Starts as `ASSIGNED`. |
| GET | `/jobs/{id}` | Signed-in member | Read Job detail fields. |
| PUT | `/jobs/{id}` | Org admin or supervisor | Replace editable Job fields and assignment. |
| PATCH | `/jobs/{id}/status` | Assigned technician, org admin, or supervisor | Move Job through its workflow. |

Status transitions: `ASSIGNED → IN_PROGRESS` or `ESCALATED`; `IN_PROGRESS → COMPLETED` or `ESCALATED`; `ESCALATED → IN_PROGRESS` or `COMPLETED`. `COMPLETED` is final. Priority is `LOW`, `NORMAL`, or `HIGH`.

### Common response format

The response model and helper live in `app/shared/response.py`; the global exception mapper lives beside them in `app/shared/errors.py`. `app/main.py` registers the mapper once. Every module imports the same response contract from `app.shared`.

Every endpoint, including login and profile, now returns this envelope:

```json
{
  "success": true,
  "message": "Job retrieved successfully.",
  "data": {"id": "550e8400-e29b-41d4-a716-446655440000"}
}
```

`data` is omitted when there is nothing useful to return (for example logout or department deletion). Login tokens now live at `response.data.access_token`; a list lives at `response.data`.

Errors use the same keys with `success: false`, the appropriate HTTP code, and a safe message. Validation errors have optional `data` containing `{field, message}` items. Expected errors map to 400/401/403/404/409/422. Database availability errors map to 503. Truly unexpected server faults still use HTTP 500, but return only a safe envelope while the detail is logged on the server. Returning a false 2xx or 4xx for a server fault would hide the failure from clients and monitoring.

## Try the phase in order

1. Run `python -m alembic upgrade head` and `python seed_dev.py` with your configured PostgreSQL database. The migration adds organizations, departments, and jobs.
2. Start the server: `python -m uvicorn app.main:app --reload`. Open `http://127.0.0.1:8000/docs`.
3. Log in with `POST /api/v1/auth/login`, then put the returned token in Swagger's **Authorize** box.
4. Create a department: `POST /api/v1/departments` with `{"name":"Maintenance","description":"Field repairs"}`. Copy its UUID.
5. Use `GET /api/v1/users/me` and read `data.id` to find your user UUID. Create a Job with:

   ```json
   {
     "department_id": "<department UUID>",
     "assigned_to_id": "<user UUID>",
     "title": "AC Maintenance",
     "description": "AC is not cooling",
     "customer": "ABC Office",
     "location": "Lahore",
     "equipment": "Model X AC",
     "priority": "HIGH"
   }
   ```

6. Try `GET /api/v1/jobs?status=ASSIGNED`, `GET /api/v1/jobs/{id}`, and `PATCH /api/v1/jobs/{id}/status` with `{"status":"IN_PROGRESS"}`.

## What comes next

Phase 1 covers the list/cards, core Job details, department list, creation, editing, assignment, and status. The design's service report, activity timeline, request categories, routing rules, escalation automation, AI context, and PDF export need separate tables and endpoints. Build service reports and activity next, then department routing; their data and behavior should be agreed with the frontend team before implementation.
