import os
import tempfile
import zipfile
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import Job, Certificate
from app.schemas import (
    JobCreate,
    JobResponse,
    JobCreateResponse,
    CertificateResponse,
)
from app.services.jobs import process_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    payload: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Creates a new bulk certificate generation job.
    Enqueues processing in background tasks and returns 202 Accepted.
    """
    total_recipients = len(payload.recipients)

    # 1. Create Job record
    job = Job(
        certificate_title=payload.certificate_title,
        event_name=payload.event_name,
        issue_date=payload.issue_date,
        status="pending",
        total=total_recipients,
        succeeded=0,
        failed=0,
    )
    db.add(job)
    db.flush()  # Generate job.id

    # 2. Create Certificate records for each recipient
    for r in payload.recipients:
        cert = Certificate(
            job_id=job.id,
            recipient_name=r.name,
            recipient_email=r.email,
            status="pending",
        )
        db.add(cert)

    db.commit()
    db.refresh(job)

    # 3. Schedule background processing passing SessionLocal factory
    background_tasks.add_task(process_job, job.id, SessionLocal)

    return JobCreateResponse(
        job_id=job.id,
        status=job.status,
        total=job.total,
        succeeded=job.succeeded,
        failed=job.failed,
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Gets overall job status, progress counts, and per-recipient status/error details.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )
    return job


@router.get("/{job_id}/certificates", response_model=List[CertificateResponse])
def get_job_certificates(job_id: str, db: Session = Depends(get_db)):
    """
    Lists generated certificate records for a specific job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )
    return job.certificates


@router.get("/{job_id}/certificates/{certificate_id}")
def download_single_certificate(
    job_id: str, certificate_id: str, db: Session = Depends(get_db)
):
    """
    Downloads a single generated PDF certificate.
    """
    cert = (
        db.query(Certificate)
        .filter(Certificate.job_id == job_id, Certificate.id == certificate_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate '{certificate_id}' for job '{job_id}' not found.",
        )

    if cert.status != "completed" or not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate file for '{certificate_id}' is not available (status: {cert.status}).",
        )

    safe_name = "".join(c for c in cert.recipient_name if c.isalnum() or c in (" ", "_", "-")).strip()
    filename = f"{safe_name}_{cert.id[:8]}.pdf" if safe_name else f"certificate_{cert.id[:8]}.pdf"

    return FileResponse(
        path=cert.file_path,
        filename=filename,
        media_type="application/pdf",
    )


@router.get("/{job_id}/download")
def download_all_certificates_zip(job_id: str, db: Session = Depends(get_db)):
    """
    Bundles all completed certificates for a job into a ZIP file download.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    completed_certs = [
        cert for cert in job.certificates if cert.status == "completed" and cert.file_path and os.path.exists(cert.file_path)
    ]

    if not completed_certs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed certificate PDFs found to download for this job.",
        )

    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_zip_path = temp_zip.name
    temp_zip.close()

    with zipfile.ZipFile(temp_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for cert in completed_certs:
            safe_name = "".join(c for c in cert.recipient_name if c.isalnum() or c in (" ", "_", "-")).strip()
            arcname = f"{safe_name}_{cert.id[:8]}.pdf" if safe_name else f"{cert.id}.pdf"
            zip_file.write(cert.file_path, arcname=arcname)

    return FileResponse(
        path=temp_zip_path,
        filename=f"certificates_{job_id[:8]}.zip",
        media_type="application/zip",
        background=None,  # Or cleanup file after response if needed
    )
