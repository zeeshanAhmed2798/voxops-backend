"""Organization member directory and UUID-backed role API tests."""

from app.models.department import Department
from app.models.organization import Organization


def _department(db, test_user, name="HR"):
    db.add(Organization(id=test_user.organization_id, name="CoolTech"))
    department = Department(
        organization_id=test_user.organization_id,
        name=name,
        description=f"{name} department",
    )
    db.add(department)
    db.commit()
    return department


def test_roles_and_invite_member_flow(client, db, test_user, auth_headers):
    department = _department(db, test_user)
    roles_response = client.get("/api/v1/team-members/roles", headers=auth_headers)
    assert roles_response.status_code == 200, roles_response.text
    roles = roles_response.json()["data"]
    assert [role["code"] for role in roles] == [
        "ORG_ADMIN", "SUPERVISOR", "DEPARTMENT_AGENT", "FIELD_WORKER", "EMPLOYEE"
    ]
    employee_role = next(role for role in roles if role["code"] == "EMPLOYEE")

    invite = client.post(
        "/api/v1/team-members",
        json={
            "email": "member@example.com",
            "full_name": "New Member",
            "role_id": employee_role["id"],
            "department_id": str(department.id),
        },
        headers=auth_headers,
    )
    assert invite.status_code == 201, invite.text
    invited = invite.json()["data"]
    assert invited["status"] == "INVITED"
    assert invited["department"]["name"] == "HR"
    assert invited["role"]["name"] == "Employee"

    listing = client.get(
        "/api/v1/team-members",
        params={"search": "new member", "status": "INVITED", "limit": 1},
        headers=auth_headers,
    )
    assert listing.status_code == 200, listing.text
    data = listing.json()["data"]
    assert data["items"][0]["email"] == "member@example.com"
    assert data["has_more"] is False

    activate = client.patch(
        f"/api/v1/team-members/{invited['id']}",
        json={"status": "ACTIVE"},
        headers=auth_headers,
    )
    assert activate.status_code == 422


def test_invite_rejects_duplicate_email_and_foreign_department(
    client, db, test_user, auth_headers
):
    department = _department(db, test_user)
    roles = client.get("/api/v1/team-members/roles", headers=auth_headers).json()["data"]
    role_id = next(role["id"] for role in roles if role["code"] == "FIELD_WORKER")
    payload = {
        "email": "duplicate@example.com",
        "full_name": "Duplicate Member",
        "role_id": role_id,
        "department_id": str(department.id),
    }
    assert client.post("/api/v1/team-members", json=payload, headers=auth_headers).status_code == 201
    assert client.post("/api/v1/team-members", json=payload, headers=auth_headers).status_code == 409

    payload["email"] = "other@example.com"
    payload["department_id"] = "00000000-0000-0000-0000-000000000099"
    assert client.post("/api/v1/team-members", json=payload, headers=auth_headers).status_code == 422
