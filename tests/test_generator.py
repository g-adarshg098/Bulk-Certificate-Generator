import os
from datetime import date
from pathlib import Path
from app.services.generator import generate_certificate_pdf


def test_generate_certificate_pdf(tmp_path: Path):
    pdf_path = tmp_path / "test_cert.pdf"
    
    result_path = generate_certificate_pdf(
        output_path=pdf_path,
        recipient_name="John Doe",
        certificate_title="Certificate of Excellence",
        event_name="AI Hackathon 2026",
        issue_date=date(2026, 10, 7),
        certificate_id="12345678-abcd-1234-abcd-1234567890ab",
    )

    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 0
    assert result_path == str(pdf_path)
