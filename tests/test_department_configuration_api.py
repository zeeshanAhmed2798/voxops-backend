"""API coverage for department categories, roles, routing, and escalation."""

from app.models.organization import Organization


def _create_department(client, db, test_user, auth_headers, name="IT"):
    db.add(Organization(id=test_user.organization_id, name="CoolTech"))
    db.commit()
    response = client.post(
        "/api/v1/departments",
        json={
            "name": name,
            "description": "Technical support for employees.",
            "categories": ["Hardware", "Network"],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_complete_department_configuration_flow(client, db, test_user, auth_headers):
    department = _create_department(client, db, test_user, auth_headers)
    department_id = department["id"]

    role_response = client.post(
        f"/api/v1/departments/{department_id}/roles",
        json={"name": "IT Support", "description": "Handles technical requests."},
        headers=auth_headers,
    )
    assert role_response.status_code == 201, role_response.text
    role_id = role_response.json()["data"]["id"]

    category_id = department["categories"][0]["id"]
    rule_response = client.post(
        f"/api/v1/departments/{department_id}/routing-rules",
        json={
            "category_id": category_id,
            "department_role_id": role_id,
            "priority_override": "HIGH",
        },
        headers=auth_headers,
    )
    assert rule_response.status_code == 201, rule_response.text
    assert rule_response.json()["data"]["category_name"] == "Hardware"
    assert rule_response.json()["data"]["department_role_name"] == "IT Support"

    escalation_response = client.put(
        f"/api/v1/departments/{department_id}/escalation",
        json={"after_hours": 24, "escalate_to_role_id": role_id, "is_enabled": True},
        headers=auth_headers,
    )
    assert escalation_response.status_code == 200, escalation_response.text

    configuration = client.get(
        f"/api/v1/departments/{department_id}/configuration", headers=auth_headers
    )
    assert configuration.status_code == 200, configuration.text
    data = configuration.json()["data"]
    assert data["department"]["name"] == "IT"
    assert {item["name"] for item in data["categories"]} == {"Hardware", "Network"}
    assert [item["name"] for item in data["roles"]] == ["IT Support"]
    assert data["routing_rules"][0]["priority_override"] == "HIGH"
    assert data["escalation_policy"]["after_hours"] == 24
    assert data["escalation_policy"]["escalate_to_role_name"] == "IT Support"


def test_routing_and_escalation_reject_resources_from_another_department(
    client, db, test_user, auth_headers
):
    first = _create_department(client, db, test_user, auth_headers, "IT")
    second_response = client.post(
        "/api/v1/departments",
        json={"name": "HR", "categories": ["Leave"]},
        headers=auth_headers,
    )
    assert second_response.status_code == 201
    second = second_response.json()["data"]

    role_response = client.post(
        f"/api/v1/departments/{second['id']}/roles",
        json={"name": "HR Supervisor"},
        headers=auth_headers,
    )
    role_id = role_response.json()["data"]["id"]

    routing = client.post(
        f"/api/v1/departments/{first['id']}/routing-rules",
        json={
            "category_id": first["categories"][0]["id"],
            "department_role_id": role_id,
            "priority_override": "NORMAL",
        },
        headers=auth_headers,
    )
    assert routing.status_code == 404

    escalation = client.put(
        f"/api/v1/departments/{first['id']}/escalation",
        json={"after_hours": 24, "escalate_to_role_id": role_id},
        headers=auth_headers,
    )
    assert escalation.status_code == 404


def test_department_list_uses_cursor_pagination_and_embeds_categories(
    client, db, test_user, auth_headers
):
    first = _create_department(client, db, test_user, auth_headers, "Finance")
    assert first["categories"]
    for name in ("HR", "IT"):
        response = client.post(
            "/api/v1/departments",
            json={"name": name, "categories": [f"{name} General"]},
            headers=auth_headers,
        )
        assert response.status_code == 201, response.text

    first_page = client.get("/api/v1/departments?limit=2", headers=auth_headers)
    assert first_page.status_code == 200, first_page.text
    first_data = first_page.json()["data"]
    assert [item["name"] for item in first_data["items"]] == ["Finance", "HR"]
    assert first_data["items"][0]["categories"][0]["name"] == "Hardware"
    assert first_data["has_more"] is True
    assert first_data["next_cursor"]

    second_page = client.get(
        "/api/v1/departments",
        params={"limit": 2, "cursor": first_data["next_cursor"]},
        headers=auth_headers,
    )
    assert second_page.status_code == 200, second_page.text
    second_data = second_page.json()["data"]
    assert [item["name"] for item in second_data["items"]] == ["IT"]
    assert second_data["has_more"] is False
    assert "next_cursor" not in second_data

    invalid = client.get(
        "/api/v1/departments?cursor=not-a-valid-cursor", headers=auth_headers
    )
    assert invalid.status_code == 422
