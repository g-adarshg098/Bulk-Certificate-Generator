from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RecipientCreate(BaseModel):
    name: str
    email: str


class JobCreate(BaseModel):
    certificate_title: str
    event_name: str
    issue_date: date
    recipients: List[RecipientCreate] = Field(..., min_length=1, max_length=1000)


class CertificateResponse(BaseModel):
    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    status: str
    error: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobResponse(BaseModel):
    id: str
    status: str
    total: int
    succeeded: int
    failed: int
    certificate_title: str
    event_name: str
    issue_date: date
    created_at: datetime
    certificates: List[CertificateResponse] = []

    model_config = ConfigDict(from_attributes=True)


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    total: int
    succeeded: int
    failed: int
