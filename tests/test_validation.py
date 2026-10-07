from datetime import date
from fastapi.testclient import TestClient


def test_validation_empty_recipients(client: TestClient):
    payload = {
        "certificate_title": "Certificate of Completion",
        "event_name": "Web Dev Bootcamp",
        "issue_date": "2026-10-07",
        "recipients": [],
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_validation_over_1000_recipients(client: TestClient):
    recipients = [{"name": f"User {i}", "email": f"user{i}@example.com"} for i in range(1001)]
    payload = {
        "certificate_title": "Certificate of Completion",
        "event_name": "Web Dev Bootcamp",
        "issue_date": "2026-10-07",
        "recipients": recipients,
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_validation_malformed_payload(client: TestClient):
    payload = {
        "event_name": "Web Dev Bootcamp",
        "recipients": [{"name": "Alice", "email": "alice@example.com"}],
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_per_recipient_failure_isolation(client: TestClient):
    payload = {
        "certificate_title": "Certificate of Achievement",
        "event_name": "Data Science Summit",
        "issue_date": "2026-10-07",
        "recipients": [
            {"name": "Valid User", "email": "valid@example.com"},
            {"name": "", "email": "blankname@example.com"},
            {"name": "Invalid Email User", "email": "not-an-email"},
        ],
    }

    res = client.post("/jobs", json=payload)
    assert res.status_code == 202
    job_id = res.json()["job_id"]
    job_res = client.get(f"/jobs/{job_id}")
    assert job_res.status_code == 200
    data = job_res.json()

    assert data["status"] == "completed_with_errors"
    assert data["total"] == 3
    assert data["succeeded"] == 1
    assert data["failed"] == 2

    certs = data["certificates"]
    cert_dict = {c["recipient_email"]: c for c in certs}

    assert cert_dict["valid@example.com"]["status"] == "completed"
    assert cert_dict["valid@example.com"]["error"] is None

    assert cert_dict["blankname@example.com"]["status"] == "failed"
    assert "blank" in cert_dict["blankname@example.com"]["error"].lower()

    assert cert_dict["not-an-email"]["status"] == "failed"
    assert "invalid email" in cert_dict["not-an-email"]["error"].lower()
