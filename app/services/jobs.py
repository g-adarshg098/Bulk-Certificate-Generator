import logging
import re
from pathlib import Path
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models import Job, Certificate
from app.services.generator import generate_certificate_pdf

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_recipient(name: str, email: str) -> None:
    if not name or not name.strip():
        raise ValueError("Recipient name cannot be blank")
    if not email or not EMAIL_REGEX.match(email.strip()):
        raise ValueError("Invalid email address format")


def process_job(job_id: str, db_factory=SessionLocal) -> None:
   
    db: Session = db_factory()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in background process.")
            return

        job.status = "processing"
        db.commit()

        certificates = (
            db.query(Certificate)
            .filter(Certificate.job_id == job_id)
            .all()
        )

        for cert in certificates:
            cert.status = "processing"
            db.commit()

            try:
               
                validate_recipient(cert.recipient_name, cert.recipient_email)

               
                output_dir = Path(settings.OUTPUT_DIR) / job_id
                pdf_path = output_dir / f"{cert.id}.pdf"

              
                generated_path = generate_certificate_pdf(
                    output_path=pdf_path,
                    recipient_name=cert.recipient_name.strip(),
                    certificate_title=job.certificate_title,
                    event_name=job.event_name,
                    issue_date=job.issue_date,
                    certificate_id=cert.id,
                )

                if not Path(generated_path).exists() or Path(generated_path).stat().st_size == 0:
                    raise RuntimeError("Generated PDF file is empty or missing")

                cert.status = "completed"
                cert.file_path = str(generated_path)
                cert.error = None
                job.succeeded += 1

            except Exception as e:
                logger.warning(f"Failed processing certificate {cert.id} for {cert.recipient_email}: {e}")
                cert.status = "failed"
                cert.error = str(e)
                cert.file_path = None
                job.failed += 1

            db.commit()

        if job.failed > 0:
            job.status = "completed_with_errors"
        else:
            job.status = "completed"

        db.commit()

    except Exception as e:
        logger.exception(f"Unexpected error in background job {job_id}: {e}")
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "completed_with_errors"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
