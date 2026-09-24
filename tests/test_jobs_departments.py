"""The Jobs and Departments API must respect organization and role boundaries."""

import uuid

from app.core.security import hash_password
# pyrefly: ignore [missing-import]
from app.models.department import Department
from app.models.department import DepartmentCategory
# pyrefly: ignore [missing-import]
from app.models.organization import Organization
from app.models.user import AppRole, User, UserRole, UserStatus


def _user(db, org_id, email, role=UserRole.EMPLOYEE):
    role_record = db.query(AppRole).filter_by(code=role.value).one()
    user = User(id=uuid.uuid4(), organization_id=org_id, name=email,
                email=email, password_hash=hash_password("ChangeMe123!"),
                user_role_id=role_record.id, status=UserStatus.ACTIVE)
    db.add(user)
    db.commit()
    return user


def _login(client, email):
    result = client.post("/api/v1/auth/login", json={"email": email, "password": "ChangeMe123!"})
    assert result.status_code == 200
    return {"Authorization": f"Bearer {result.json()['data']['access_token']}"}


def _job(department_id, assigned_to_id):
    return {"department_id": str(department_id), "assigned_to_id": str(assigned_to_id),
            "title": "AC Maintenance", "customer": "ABC Office", "location": "Lahore",
            "equipment": "Model X AC", "priority": "HIGH"}


def test_department_and_job_flow(client, db, test_user, auth_headers):
    db.add(Organization(id=test_user.organization_id, name="CoolTech"))
    db.commit()
    technician = _user(db, test_user.organization_id, "tech@example.com")
    tech_headers = _login(client, technician.email)

    response = client.post("/api/v1/departments", json={"name": "Maintenance", "description": "Field repairs"}, headers=auth_headers)
    assert response.status_code == 201, response.text
    department_id = response.json()["data"]["id"]
    assert client.get("/api/v1/departments", headers=tech_headers).json()["data"]["items"][0]["name"] == "Maintenance"
    assert client.post("/api/v1/departments", json={"name": "Maintenance"}, headers=auth_headers).status_code == 409
    assert client.post("/api/v1/departments", json={"name": "IT"}, headers=tech_headers).status_code == 403

    response = client.post("/api/v1/jobs", json=_job(department_id, technician.id), headers=auth_headers)
    assert response.status_code == 201, response.text
    job_id = response.json()["data"]["id"]
    assert uuid.UUID(job_id)
    assert response.json()["data"]["status"] == "ASSIGNED"
    assert client.get("/api/v1/jobs?status=ASSIGNED&assigned_to_me=true", headers=tech_headers).json()["data"][0]["id"] == job_id
    assert client.get(f"/api/v1/jobs/{job_id}", headers=tech_headers).status_code == 200
    assert client.post("/api/v1/jobs", json=_job(department_id, technician.id), headers=tech_headers).status_code == 403
    assert client.delete(f"/api/v1/departments/{department_id}", headers=auth_headers).status_code == 409
    assert client.patch(f"/api/v1/jobs/{job_id}/status", json={"status": "COMPLETED"}, headers=tech_headers).status_code == 409
    assert client.patch(f"/api/v1/jobs/{job_id}/status", json={"status": "IN_PROGRESS"}, headers=tech_headers).status_code == 200
    assert client.patch(f"/api/v1/jobs/{job_id}/status", json={"status": "COMPLETED"}, headers=tech_headers).status_code == 200


def test_create_department_with_categories(client, db, test_user, auth_headers):
    db.add(Organization(id=test_user.organization_id, name="CoolTech"))
    db.commit()

    response = client.post(
        "/api/v1/departments",
        json={
            "name": "HR",
            "description": "People operations",
            "categories": [" Leave ", "Payroll", "Employee Concerns"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["name"] == "HR"
    assert [category["name"] for category in data["categories"]] == [
        "Leave",
        "Payroll",
        "Employee Concerns",
    ]
    assert all(category["is_active"] for category in data["categories"])
    persisted = db.query(DepartmentCategory).filter_by(department_id=uuid.UUID(data["id"])).all()
    assert [category.name for category in persisted] == ["Leave", "Payroll", "Employee Concerns"]


def test_create_department_categories_are_optional_and_icon_is_not_accepted(
    client, db, test_user, auth_headers
):
    db.add(Organization(id=test_user.organization_id, name="CoolTech"))
    db.commit()

    response = client.post(
        "/api/v1/departments",
        json={"name": "Finance"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["categories"] == []

    response = client.post(
        "/api/v1/departments",
        json={"name": "IT", "icon": "IT"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_department_rejects_duplicate_categories(client, db, test_user, auth_headers):
    db.add(Organization(id=test_user.organization_id, name="CoolTech"))
    db.commit()

    response = client.post(
        "/api/v1/departments",
        json={"name": "HR", "categories": ["Leave", " leave "]},
        headers=auth_headers,
    )

    assert response.status_code == 422
    assert db.query(Department).filter_by(name="HR").first() is None


def test_cross_org_links_and_reads_are_rejected(client, db, test_user, auth_headers):
    own_org_id = test_user.organization_id
    other_org_id = uuid.uuid4()
    db.add_all([Organization(id=own_org_id, name="Own"), Organization(id=other_org_id, name="Other")])
    db.commit()
    own_dept = Department(id=uuid.uuid4(), organization_id=own_org_id, name="Own")
    other_dept = Department(id=uuid.uuid4(), organization_id=other_org_id, name="Other")
    db.add_all([own_dept, other_dept])
    db.commit()
    other_user = _user(db, other_org_id, "other@example.com", UserRole.ORG_ADMIN)
    other_headers = _login(client, other_user.email)

    assert client.get(f"/api/v1/departments/{other_dept.id}", headers=auth_headers).status_code == 404
    assert client.post("/api/v1/jobs", json=_job(other_dept.id, test_user.id), headers=auth_headers).status_code == 422
    assert client.post("/api/v1/jobs", json=_job(own_dept.id, other_user.id), headers=auth_headers).status_code == 422
    result = client.post("/api/v1/jobs", json=_job(own_dept.id, test_user.id), headers=auth_headers)
    assert result.status_code == 201
    job_id = result.json()["data"]["id"]
    assert client.get(f"/api/v1/jobs/{job_id}", headers=other_headers).status_code == 404
    assert client.get("/api/v1/jobs", headers=other_headers).json()["data"] == []
    assert client.put(f"/api/v1/jobs/{job_id}", json=_job(other_dept.id, other_user.id), headers=other_headers).status_code == 404
