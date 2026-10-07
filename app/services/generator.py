import os
from datetime import date
from pathlib import Path
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas


def generate_certificate_pdf(
    output_path: str | Path,
    recipient_name: str,
    certificate_title: str,
    event_name: str,
    issue_date: date | str,
    certificate_id: str,
) -> str:
   
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    width, height = landscape(letter)

    c = canvas.Canvas(str(output_path_obj), pagesize=(width, height))

    c.setFillColor(HexColor("#FAF9F6"))
    c.rect(0, 0, width, height, fill=True, stroke=False)

    c.setStrokeColor(HexColor("#1E3A8A"))
    c.setLineWidth(4)
    c.rect(20, 20, width - 40, height - 40)

    c.setStrokeColor(HexColor("#D97706"))
    c.setLineWidth(1.5)
    c.rect(26, 26, width - 52, height - 52)

    c.setFillColor(HexColor("#1E3A8A"))
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width / 2.0, height - 100, certificate_title.upper())

    c.setFillColor(HexColor("#4B5563"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2.0, height - 140, "THIS CERTIFICATE IS PROUDLY PRESENTED TO")

    c.setFillColor(HexColor("#111827"))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2.0, height - 200, recipient_name)

    c.setStrokeColor(HexColor("#D97706"))
    c.setLineWidth(2)
    c.line(width / 2.0 - 150, height - 215, width / 2.0 + 150, height - 215)

    
    c.setFillColor(HexColor("#374151"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2.0, height - 260, "for outstanding participation in")

    c.setFillColor(HexColor("#1E3A8A"))
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2.0, height - 300, event_name)
    issue_date_str = issue_date.isoformat() if isinstance(issue_date, date) else str(issue_date)

    c.setFillColor(HexColor("#6B7280"))
    c.setFont("Helvetica", 10)
    c.drawString(50, 60, f"Date of Issue: {issue_date_str}")
    c.drawRightString(width - 50, 60, f"Certificate ID: {certificate_id}")

   
    c.setStrokeColor(HexColor("#1E3A8A"))
    c.setLineWidth(1)
    c.line(width / 2.0 - 80, 70, width / 2.0 + 80, 70)
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width / 2.0, 55, "Authorized Verification")

    c.showPage()
    c.save()

    return str(output_path_obj)
