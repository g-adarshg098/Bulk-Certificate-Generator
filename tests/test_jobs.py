import io
import zipfile
from unittest.mock import patch
from fastapi.testclient import TestClient


def test_create_and_complete_job(client: TestClient):
    payload = {
        "certificate_title": "Certificate of Excellence",
        "event_name": "Python Conference 2026",
        "issue_date": "2026-10-07",
        "recipients": [
            {"name": "Alice Smith", "email": "alice@example.com"},
            {"name": "Bob Jones", "email": "bob@example.com"},
        ],
    }


    response = client.post("/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    assert data["total"] == 2
    assert data["succeeded"] == 0
    assert data["failed"] == 0

    job_id = data["job_id"]

   
    status_res = client.get(f"/jobs/{job_id}")
    assert status_res.status_code == 200
    job_data = status_res.json()
    assert job_data["status"] == "completed"
    assert job_data["total"] == 2
    assert job_data["succeeded"] == 2
    assert job_data["failed"] == 0
    assert len(job_data["certificates"]) == 2

  
    certs_res = client.get(f"/jobs/{job_id}/certificates")
    assert certs_res.status_code == 200
    certs_list = certs_res.json()
    assert len(certs_list) == 2
    
    cert_id = certs_list[0]["id"]

 
    pdf_res = client.get(f"/jobs/{job_id}/certificates/{cert_id}")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_content := pdf_res.content) > 0

   
    zip_res = client.get(f"/jobs/{job_id}/download")
    assert zip_res.status_code == 200
    assert zip_res.headers["content-type"] == "application/zip"
    

    with zipfile.ZipFile(io.BytesIO(zip_res.content)) as z:
        file_list = z.namelist()
        assert len(file_list) == 2
        for name in file_list:
            assert name.endswith(".pdf")


def test_generator_exception_isolation(client: TestClient):
   
    payload = {
        "certificate_title": "Certificate of Merit",
        "event_name": "Hackathon 2026",
        "issue_date": "2026-10-07",
        "recipients": [
            {"name": "Charlie Brown", "email": "charlie@example.com"},
            {"name": "Error User", "email": "error@example.com"},
        ],
    }

    from app.services.jobs import generate_certificate_pdf as original_generator

    def mock_generator(*args, **kwargs):
        if kwargs.get("recipient_name") == "Error User":
            raise RuntimeError("ReportLab canvas render exception simulated")
        return original_generator(*args, **kwargs)

    with patch("app.services.jobs.generate_certificate_pdf", side_effect=mock_generator):
        response = client.post("/jobs", json=payload)
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        status_res = client.get(f"/jobs/{job_id}")
        assert status_res.status_code == 200
        job_data = status_res.json()

        assert job_data["status"] == "completed_with_errors"
        assert job_data["succeeded"] == 1
        assert job_data["failed"] == 1

        certs_by_email = {c["recipient_email"]: c for c in job_data["certificates"]}
        assert certs_by_email["charlie@example.com"]["status"] == "completed"
        assert certs_by_email["error@example.com"]["status"] == "failed"
        assert "ReportLab canvas render exception" in certs_by_email["error@example.com"]["error"]


def test_job_not_found(client: TestClient):
    res = client.get("/jobs/non-existent-uuid")
    assert res.status_code == 404
