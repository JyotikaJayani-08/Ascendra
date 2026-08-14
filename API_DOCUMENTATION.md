# Ascendra REST API Specification

This document provides a comprehensive reference for the Ascendra REST API (`v1`), including endpoint signatures, authentication models, request parameters, payload structures, and response schemas.

---

## 1. Architecture and Conventions

### 1.1 Base URLs
- **Local Development**: `http://localhost:8000`
- **API v1 Prefix**: `/api/v1`

### 1.2 Authentication
All protected endpoints require an authorization token passed via the HTTP `Authorization` header:
```http
Authorization: Bearer <JWT_ACCESS_TOKEN>
```
Tokens are generated through Supabase Auth or the internal JWT authentication service.

### 1.3 Error Responses
The API adheres to the **RFC 7807 Problem Details** standard for all error responses:
```json
{
  "type": "about:blank",
  "title": "VALIDATION_ERROR",
  "status": 422,
  "detail": "Invalid input parameters.",
  "instance": "/api/v1/resumes",
  "errors": [
    {
      "loc": ["body", "file"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## 2. Endpoint Index

| Category | Method | Path | Description | Auth Required |
| :--- | :--- | :--- | :--- | :---: |
| **System** | `GET` | `/health` | API health check and environment status | No |
| **Auth** | `POST` | `/api/v1/auth/cookie/set` | Set secure HTTP-only refresh token cookie | No |
| | `POST` | `/api/v1/auth/refresh` | Rotate refresh token and issue new access token | Cookie |
| | `POST` | `/api/v1/auth/logout` | Revoke token and clear session cookies | Cookie |
| **Google OAuth** | `GET` | `/api/v1/auth/google/authorize` | Initiate Google OAuth 2.0 consent for Gmail API | Yes |
| | `GET` | `/api/v1/auth/google/callback` | Handle OAuth 2.0 authorization code exchange | No |
| **User Profile** | `GET` | `/api/v1/users/me` | Fetch authenticated user profile | Yes |
| | `PATCH` | `/api/v1/users/me` | Update authenticated user profile | Yes |
| | `DELETE` | `/api/v1/users/me` | Delete account and all associated data | Yes |
| **Email Config** | `GET` | `/api/v1/users/me/email-config` | Get configured SMTP/OAuth provider settings | Yes |
| | `POST` | `/api/v1/users/me/email-config` | Register or update SMTP provider settings | Yes |
| | `POST` | `/api/v1/users/me/email-config/test` | Dispatch test email to verify credentials | Yes |
| | `DELETE` | `/api/v1/users/me/email-config` | Disconnect and remove email provider configuration | Yes |
| **Resumes** | `POST` | `/api/v1/resumes` | Upload a PDF resume (max 5 MB) | Yes |
| | `GET` | `/api/v1/resumes` | List all uploaded resumes for user | Yes |
| | `GET` | `/api/v1/resumes/{resume_id}` | Retrieve specific resume and parsed payload | Yes |
| | `DELETE` | `/api/v1/resumes/{resume_id}` | Delete a specific resume | Yes |
| | `POST` | `/api/v1/resumes/{resume_id}/reparse` | Trigger background re-parsing of resume PDF | Yes |
| | `POST` | `/api/v1/resumes/bulk-delete` | Bulk delete specified resumes | Yes |
| | `DELETE` | `/api/v1/resumes/delete-all` | Delete all resumes belonging to user | Yes |
| **Resume Versions** | `GET` | `/api/v1/resume-versions` | List all tailored resume versions | Yes |
| | `GET` | `/api/v1/resumes/{resume_id}/versions` | List all tailored versions for a specific resume | Yes |
| | `POST` | `/api/v1/resume-versions/{version_id}/approve` | Mark a generated resume version as approved | Yes |
| | `GET` | `/api/v1/resume-versions/{version_id}/compare` | Structural diff between version and original resume | Yes |
| | `DELETE` | `/api/v1/resume-versions/{version_id}` | Delete a specific tailored version | Yes |
| | `POST` | `/api/v1/resume-versions/bulk-delete` | Bulk delete tailored versions | Yes |
| | `DELETE` | `/api/v1/resume-versions/delete-all` | Delete all tailored versions | Yes |
| **Jobs** | `GET` | `/api/v1/jobs` | Search, filter, and paginate job opportunities | Yes |
| | `POST` | `/api/v1/jobs` | Create a job opportunity manually | Yes |
| | `GET` | `/api/v1/jobs/{job_id}` | Retrieve job details and company metadata | Yes |
| | `DELETE` | `/api/v1/jobs/{job_id}` | Delete a job opportunity | Yes |
| | `POST` | `/api/v1/jobs/sync` | Ingest external jobs from provider search engines | Yes |
| **Contacts** | `POST` | `/api/v1/contacts` | Manually add a recruiter or hiring contact | Yes |
| | `GET` | `/api/v1/contacts` | List contacts associated with user | Yes |
| | `GET` | `/api/v1/contacts/{contact_id}` | Get specific contact details | Yes |
| | `PATCH` | `/api/v1/contacts/{contact_id}` | Update contact attributes | Yes |
| | `DELETE` | `/api/v1/contacts/{contact_id}` | Delete a specific contact | Yes |
| | `DELETE` | `/api/v1/contacts/all` | Delete all user contacts | Yes |
| | `POST` | `/api/v1/contacts/discover` | Run 3-layer recruiter discovery for a company | Yes |
| | `GET` | `/api/v1/companies/{company_id}/contacts` | List ranked contacts for a company | Yes |
| **AI Workflows** | `POST` | `/api/v1/ai/resume/generate` | Generate tailored resume targeting a specific job | Yes |
| | `POST` | `/api/v1/ai/email/generate` | Generate personalized initial outreach email draft | Yes |
| | `POST` | `/api/v1/ai/email/followup` | Generate contextual follow-up email draft | Yes |
| **Outreach & Email** | `POST` | `/api/v1/email/draft` | Create a new manual or template email draft | Yes |
| | `POST` | `/api/v1/email/{message_id}/edit` | Update email content prior to dispatch | Yes |
| | `POST` | `/api/v1/email/{message_id}/approve` | Mark message as approved for dispatch | Yes |
| | `POST` | `/api/v1/email/{message_id}/send` | Queue approved message to worker for delivery | Yes |
| | `POST` | `/api/v1/email/{message_id}/schedule` | Schedule message for future automated sending | Yes |
| | `POST` | `/api/v1/email/{message_id}/reschedule` | Update scheduled dispatch timestamp | Yes |
| | `POST` | `/api/v1/email/{message_id}/cancel-schedule`| Revert scheduled message back to approved state | Yes |
| | `GET` | `/api/v1/email/track/open/{message_id}` | Transparent 1x1 GIF tracking pixel for opens | No |
| | `GET` | `/api/v1/email/track/click/{message_id}` | Redirect endpoint for recording outbound clicks | No |
| **Conversations** | `GET` | `/api/v1/conversations` | List conversation threads with recruiters | Yes |
| | `GET` | `/api/v1/conversations/{id}/messages` | List all chronological messages in thread | Yes |
| **Follow-ups** | `POST` | `/api/v1/followups/schedule` | Schedule automated follow-up timer for thread | Yes |
| | `GET` | `/api/v1/followups` | List all pending scheduled follow-ups | Yes |
| | `DELETE` | `/api/v1/followups/{followup_id}` | Cancel a scheduled follow-up | Yes |
| **Applications** | `GET` | `/api/v1/applications` | List applications with pagination and filters | Yes |
| | `POST` | `/api/v1/applications` | Create a new job application record (DRAFT) | Yes |
| | `GET` | `/api/v1/applications/stats` | Aggregate counts of applications per status | Yes |
| | `GET` | `/api/v1/applications/{app_id}` | Get application record by ID | Yes |
| | `PATCH` | `/api/v1/applications/{app_id}` | Update application attributes | Yes |
| | `POST` | `/api/v1/applications/{app_id}/transition` | Update lifecycle state (e.g. DRAFT -> APPLIED) | Yes |
| | `DELETE` | `/api/v1/applications/{app_id}` | Archive or soft delete an application | Yes |
| **Dashboard** | `GET` | `/api/v1/dashboard` | Main metrics summary and application counts | Yes |
| | `GET` | `/api/v1/dashboard/funnel-velocity` | Funnel metrics, conversion times, response rates | Yes |
| | `GET` | `/api/v1/dashboard/recent-activity` | Chronological activity feed | Yes |
| **Notes** | `GET` | `/api/v1/notes` | List all user notes | Yes |
| | `POST` | `/api/v1/notes` | Create a new application/job note | Yes |
| | `GET` | `/api/v1/notes/{note_id}` | Retrieve specific note | Yes |
| | `PATCH` | `/api/v1/notes/{note_id}` | Update note title or body | Yes |
| | `DELETE` | `/api/v1/notes/{note_id}` | Delete a note | Yes |
| **Notifications** | `GET` | `/api/v1/notifications` | List notifications (all or unread only) | Yes |
| | `POST` | `/api/v1/notifications/{id}/read` | Mark individual notification as read | Yes |
| | `POST` | `/api/v1/notifications/read-all` | Mark all notifications as read | Yes |
| | `GET` | `/api/v1/notifications/stream` | Server-Sent Events (SSE) stream for real-time alerts | Yes (Token Query) |

---

## 3. Detailed Request and Response Examples

### 3.1 Upload Resume
- **Endpoint**: `POST /api/v1/resumes`
- **Headers**: `Content-Type: multipart/form-data`
- **Body**: `file`: Binary PDF file (Max 5 MB)

**Response (`201 Created`):**
```json
{
  "id": "8f3b2c1a-5d9a-4e2f-b4e8-76a94b8e21d3",
  "user_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "filename": "john_doe_resume.pdf",
  "file_url": "https://your-project.supabase.co/storage/v1/object/public/resumes/...",
  "status": "PROCESSING",
  "parsed_data": null,
  "created_at": "2026-08-14T14:00:00Z",
  "updated_at": "2026-08-14T14:00:00Z"
}
```

---

### 3.2 Generate AI Resume
- **Endpoint**: `POST /api/v1/ai/resume/generate`
- **Headers**: `Content-Type: application/json`

**Request Body:**
```json
{
  "resume_id": "8f3b2c1a-5d9a-4e2f-b4e8-76a94b8e21d3",
  "job_id": "4a7c1b2d-3e5f-4a6b-8c9d-0e1f2a3b4c5d",
  "label": "Senior Backend Engineer - Google",
  "tailoring_style": "ATS_OPTIMIZED",
  "focus_keywords": ["FastAPI", "Distributed Systems", "PostgreSQL"],
  "custom_instructions": "Highlight asynchronous architecture and latency reductions."
}
```

**Response (`200 OK`):**
```json
{
  "success": true,
  "data": {
    "version_id": "5f2c1b3d-4e6a-4c8d-9b0e-1f2a3b4c5d6e",
    "resume_id": "8f3b2c1a-5d9a-4e2f-b4e8-76a94b8e21d3",
    "version_number": 2,
    "label": "Senior Backend Engineer - Google",
    "status": "DRAFT",
    "tailored_data": {
      "skills": ["Python", "FastAPI", "Distributed Systems", "PostgreSQL"],
      "experience": [...]
    },
    "ats_match_score": 92.5,
    "changes_summary": "Reordered technical skills and emphasized async database querying in experience bullet points."
  }
}
```

---

### 3.3 Generate AI Outreach Email
- **Endpoint**: `POST /api/v1/ai/email/generate`
- **Headers**: `Content-Type: application/json`

**Request Body:**
```json
{
  "application_id": "3d2b1a0f-9c8e-4a7b-6c5d-4e3f2a1b0c9d",
  "tone": "PROFESSIONAL"
}
```

**Response (`200 OK`):**
```json
{
  "success": true,
  "data": {
    "message_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "subject": "Application for Senior Backend Engineer - John Doe",
    "body_text": "Hi Jane,\n\nI noticed the Senior Backend Engineer role at Acme Corp...",
    "body_html": "<p>Hi Jane,</p><p>I noticed the Senior Backend Engineer role at Acme Corp...</p>",
    "status": "DRAFT"
  }
}
```

---

### 3.4 Search and Filter Jobs
- **Endpoint**: `GET /api/v1/jobs?title=Backend&remote_status=REMOTE&page=1&page_size=25`

**Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "4a7c1b2d-3e5f-4a6b-8c9d-0e1f2a3b4c5d",
      "title": "Senior Backend Engineer",
      "location": "San Francisco, CA",
      "remote_status": "REMOTE",
      "employment_type": "FULL_TIME",
      "experience_level": "SENIOR",
      "salary_min": 160000,
      "salary_max": 200000,
      "currency": "USD",
      "company": {
        "id": "1c2d3e4f-5a6b-7c8d-9e0f-1a2b3c4d5e6f",
        "name": "Acme Corporation",
        "domain": "acmecorp.com",
        "logo_url": "https://img.logo.dev/acmecorp.com"
      },
      "created_at": "2026-08-14T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 25
}
```

---

### 3.5 Real-Time Notifications (Server-Sent Events)
- **Endpoint**: `GET /api/v1/notifications/stream?token=<ACCESS_TOKEN>`
- **Headers**: `Accept: text/event-stream`

**Stream Output Example:**
```text
event: notification
data: {"id": "a1b2c3d4", "title": "Email Opened", "message": "Jane Doe opened your email for Senior Backend Engineer.", "type": "EMAIL_OPENED", "created_at": "2026-08-14T14:30:00Z"}

event: ping
data: {"timestamp": 1723645800}
```
