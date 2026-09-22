"""The Jobs and Departments API must respect organization and role boundaries."""

import uuid

from app.core.security import hash_password
# pyrefly: ignore [missing-import]
from app.models.department import Department
# pyrefly: ignore [missing-import]
from app.models.organization import Organization
from app.models.user import User, UserRole, UserStatus


def _user(db, org_id, email, role=UserRole.EMPLOYEE):
    user = User(id=uuid.uuid4(), organization_id=org_id, name=email,
                email=email, password_hash=hash_password("ChangeMe123!"),
                role=role, status=UserStatus.ACTIVE)
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
    assert client.get("/api/v1/departments", headers=tech_headers).json()["data"][0]["name"] == "Maintenance"
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
