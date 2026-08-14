"""
Ascendra — Job Schemas.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class CompanyResponse(BaseModel):
    id: str
    name: str
    domain: str | None = None
    logo_url: str | None = None
    website: str | None = None
    industry: str | None = None
    size: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    id: str
    company_id: str
    title: str
    description: str | None = None
    requirements: str | None = None
    location: str | None = None
    remote_status: str
    employment_type: str
    experience_level: str
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    source_url: str | None = None
    status: str
    provider_name: str | None = None
    posted_date: date | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobWithCompanyResponse(JobResponse):
    company: CompanyResponse | None = None


class JobListResponse(BaseModel):
    items: list[JobWithCompanyResponse]
    total: int
    page: int
    page_size: int


class JobSearchParams(BaseModel):
    title: str | None = None
    location: str | None = None
    remote_status: str | None = None
    employment_type: str | None = None
    experience_level: str | None = None
    company_name: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class CreateJobRequest(BaseModel):
    """For manual job entry by users."""
    title: str = Field(max_length=500)
    company_name: str = Field(max_length=255)
    description: str | None = None
    requirements: str | None = None
    location: str | None = None
    remote_status: str = "UNKNOWN"
    employment_type: str = "UNKNOWN"
    experience_level: str = "UNKNOWN"
    source_url: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None


class SyncJobRequest(BaseModel):
    provider_name: str = Field(..., description="serpapi, remotive, jobicy, remoteok, weworkremotely")
    country_code: str = "us"
    # Legacy search params
    what: str | None = None
    where: str | None = None
    page: int = Field(default=1, ge=1)
    results_per_page: int = Field(default=20, ge=1, le=100)
    # SerpApi / Instahyre-grade filter params
    query: str | None = None
    location: str | None = None
    is_remote: bool = False
    company: str | None = None
    experience_level: str | None = None
    employment_type: str | None = None


class SyncJobResponse(BaseModel):
    provider: str
    synced: int
    skipped_or_updated: int
