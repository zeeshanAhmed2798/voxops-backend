"""Shared response and error behavior that the frontend can rely on."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.models.organization import Organization


def test_envelope_for_success_validation_and_http_errors(client, db, test_user, auth_headers):
    success = client.get("/api/v1/auth/me", headers=auth_headers)
    assert success.status_code == 200
    assert success.json()["success"] is True
    assert success.json()["data"]["id"] == str(test_user.id)

    invalid = client.get("/api/v1/jobs/not-a-uuid", headers=auth_headers)
    assert invalid.status_code == 422
    assert invalid.json()["success"] is False
    assert invalid.json()["message"] == "Request validation failed."
    assert invalid.json()["data"][0]["field"] == "path.job_id"

    missing = client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=auth_headers)
    assert missing.status_code == 404
    assert missing.json() == {"success": False, "message": "Job not found."}

    unauthorized = client.get("/api/v1/jobs")
    assert unauthorized.status_code == 401
    assert unauthorized.json()["success"] is False
    assert unauthorized.headers["www-authenticate"] == "Bearer"

    db.add(Organization(id=test_user.organization_id, name="CoolTech"))
    db.commit()
    body = {"name": "Maintenance"}
    assert client.post("/api/v1/departments", json=body, headers=auth_headers).status_code == 201
    duplicate = client.post("/api/v1/departments", json=body, headers=auth_headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["success"] is False
    assert "data" not in duplicate.json()


def test_unexpected_and_database_errors_are_sanitized():
    def fail_unexpected():
        raise RuntimeError("private server detail")

    def fail_database():
        raise OperationalError("SELECT secret", {}, RuntimeError("database unavailable"))

    app.add_api_route("/__test_unexpected", fail_unexpected)
    app.add_api_route("/__test_database", fail_database)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            unexpected = client.get("/__test_unexpected")
            database = client.get("/__test_database")
        assert unexpected.status_code == 500
        assert unexpected.json() == {"success": False, "message": "An unexpected server error occurred."}
        assert "private server detail" not in unexpected.text
        assert database.status_code == 503
        assert database.json() == {"success": False, "message": "Database is temporarily unavailable."}
        assert "SELECT secret" not in database.text
    finally:
        app.router.routes[:] = [route for route in app.router.routes
                                if getattr(route, "path", None) not in {"/__test_unexpected", "/__test_database"}]
