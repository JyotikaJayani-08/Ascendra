# Swagger UI & OpenAPI Interactive Testing Guide

This guide explains how to use **Swagger UI** (OpenAPI) and **ReDoc** to explore, test, and debug all Ascendra API endpoints directly in your web browser without writing custom code or curl commands.

---

## 1. What is Swagger UI?

**Swagger UI** is an interactive, auto-generated web interface that visualizes and allows real-time interaction with the API's resources. Because Ascendra is built with **FastAPI**, OpenAPI (formerly Swagger) schemas are automatically generated from Python type hints and Pydantic models.

### Available Documentation Interfaces

When your backend server is running locally (`http://localhost:8000`):

| Interface | URL | Purpose |
| :--- | :--- | :--- |
| **Swagger UI** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive testing sandbox to execute requests directly in browser |
| **ReDoc** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Clean, searchable, publication-ready API documentation |
| **OpenAPI Schema** | [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) | Raw JSON specification for importing into Postman, Insomnia, or code generators |

---

## 2. Step-by-Step Interactive Testing Workflow

### Step 1: Start the Backend Server
Make sure the backend server is running in development mode:
```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Open Swagger UI
Navigate to **[http://localhost:8000/docs](http://localhost:8000/docs)** in your browser. You will see all API routes grouped by tags:
- `Authentication`
- `Google OAuth`
- `Profile`
- `Email Configuration`
- `Resumes`
- `Jobs`
- `Contacts`
- `AI`
- `Email`
- `Applications`
- `Dashboard`
- `Notes`
- `Notifications`
- `System`

---

### Step 3: Authenticate Protected Endpoints

Most endpoints in Ascendra require an authenticated user session:

1. Obtain a valid **JWT Access Token** (or Supabase auth token).
2. Click the green **`Authorize`** button (with lock icon) at the top right of the Swagger UI page.
3. In the dialog, enter your token in the **Value** field:
   ```text
   Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
   *(Or just the token string depending on the security scheme definition)*.
4. Click **Authorize** and then **Close**.
5. All subsequent requests executed in Swagger will automatically include the `Authorization: Bearer <token>` header.

---

### Step 4: Execute an Endpoint Request

1. Click on any endpoint block (for example, `POST /api/v1/ai/resume/generate` or `GET /api/v1/jobs`).
2. Click the **"Try it out"** button in the upper right of that endpoint panel.
3. Fill in the query parameters or edit the JSON request body directly in the editor.
4. Click the large blue **"Execute"** button.
5. Review the results:
   - **Request URL**: The exact full URL generated with query parameters.
   - **Curl**: The equivalent curl command line that you can copy and run in your terminal.
   - **Server Response**: Status Code (`200 OK`, `201 Created`, `401 Unauthorized`, `422 Unprocessable Entity`), response headers, and the JSON response body.

---

## 3. Testing Common Scenarios in Swagger UI

### 3.1 Testing File Uploads (Resumes)
1. Expand `POST /api/v1/resumes`.
2. Click **Try it out**.
3. Click the **Choose File** button under the `file` field.
4. Select a local PDF file (under 5 MB).
5. Click **Execute**.
6. Check the response body for `id`, `filename`, `file_url`, and initial status (`PROCESSING` or `UPLOADED`).

---

### 3.2 Testing AI Email & Resume Generation
1. Expand `POST /api/v1/ai/resume/generate`.
2. Click **Try it out**.
3. Provide valid UUIDs for `resume_id` and `job_id`.
4. Click **Execute**.
5. Swagger will display the streamed or completed AI generated payload, ATS match score, and version ID.

---

### 3.3 Testing Error Handling & Validation
If you send invalid types or omit required fields:
- Swagger will return a **`422 Unprocessable Entity`** error formatted per RFC 7807, highlighting precisely which parameter or field failed validation.

---

## 4. Importing into Postman or Insomnia

If you prefer external API client tools:

1. Open Postman or Insomnia.
2. Select **Import**.
3. Choose **Link / URL** and paste:
   ```
   http://localhost:8000/openapi.json
   ```
4. Postman will automatically generate a complete workspace collection containing all endpoints, path parameters, and request body templates.

---

## 5. Summary of HTTP Status Codes in Swagger

| Status Code | Meaning | Common Cause |
| :--- | :--- | :--- |
| **`200 OK`** | Success | Request processed and returned data |
| **`201 Created`** | Created | Resource successfully created (resume upload, job created, draft generated) |
| **`204 No Content`** | Success (No Body) | Resource successfully deleted |
| **`400 Bad Request`** | Client Error | Invalid format (e.g. non-PDF upload or unverified SMTP config) |
| **`401 Unauthorized`** | Authentication Required | Missing, expired, or invalid Bearer token |
| **`403 Forbidden`** | Permission Denied | Invalid internal secret or attempting to access another user's data |
| **`404 Not Found`** | Resource Missing | Specified ID (resume, job, application) does not exist |
| **`422 Unprocessable`** | Schema Validation Failure | Missing required JSON fields or invalid data types |
| **`429 Too Many Requests`**| Rate Limited | Exceeded per-minute or per-hour rate limiter |
| **`500 Internal Error`** | Server Error | Unhandled exception (check backend console logs) |
