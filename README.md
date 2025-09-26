# Alma Assessment - Leads Management API

A FastAPI-based leads management system that allows prospects to submit applications and attorneys to manage leads through a secure API.

## Features

- **Public lead submission** with file upload to AWS S3
- **Secure authentication** with JWT tokens
- **Role-based access control** (Admin and Attorney roles)
- **Email notifications** with failure tracking and recovery
- **UUID-based lead identification** for security
- **Rate limiting** to prevent spam
- **Failed email management** for administrators

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database
- AWS S3 bucket
- SMTP email service (optional)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env`:
   ```env
   DATABASE_URL=postgresql://user:password@localhost/leads_db
   SECRET_KEY=your-secret-key-here
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_S3_BUCKET_NAME=your-bucket-name
   AWS_REGION=us-east-1
   MAIL_USERNAME=your-email@example.com
   MAIL_PASSWORD=your-email-password
   MAIL_FROM=your-email@example.com
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   ```
4. Run database migrations:
   ```bash
   alembic upgrade head
   ```
5. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

### Authentication

All protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

### Public Endpoints

#### Submit Lead Application
**POST** `/leads/`

Submit a new lead application (public endpoint).

**Request:**
- `first_name` (string): Lead's first name
- `last_name` (string): Lead's last name
- `email` (string): Lead's email address
- `resume` (file): Resume/CV file (PDF, DOC, DOCX, TXT, RTF)

**Rate Limiting:** 5 submissions per minute per IP

**Response:**
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "resume_download_url": "http://localhost:8000/leads/550e8400-e29b-41d4-a716-446655440000/resume",
  "status": "PENDING",
  "created_at": "2025-09-26T19:42:27.248539",
  "updated_at": "2025-09-26T19:42:27.248544"
}
```

**Error Responses:**
- `400`: Invalid email format or file validation failed
- `413`: File too large (max 10MB)
- `429`: Rate limit exceeded

### Authentication Endpoints

#### Login
**POST** `/token`

Authenticate and receive JWT token.

**Request:**
```
Content-Type: application/x-www-form-urlencoded
username=user@example.com&password=yourpassword
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

#### Create Initial User
**POST** `/users/initial`

Create the first admin user (only works if no users exist).

**Request:**
- `email` (string): Admin email
- `password` (string): Admin password

**Response:**
```json
{
  "id": 1,
  "email": "admin@example.com",
  "role": "ADMIN",
  "is_active": true,
  "created_at": "2025-09-26T19:42:27.248539",
  "updated_at": "2025-09-26T19:42:27.248544"
}
```

### Lead Management (Attorney/Admin)

#### List All Leads
**GET** `/leads/`

Get all leads (requires authentication).

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
[
  {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "resume_download_url": "http://localhost:8000/leads/550e8400-e29b-41d4-a716-446655440000/resume",
    "status": "PENDING",
    "created_at": "2025-09-26T19:42:27.248539",
    "updated_at": "2025-09-26T19:42:27.248544"
  }
]
```

#### Get Single Lead
**GET** `/leads/{lead_uuid}`

Get a specific lead by UUID.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** Same as lead creation response

#### Update Lead Status
**PUT** `/leads/{lead_uuid}/status`

Update a lead's status.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "status": "REACHED_OUT"
}
```

**Available Statuses:**
- `PENDING`: Default status for new leads
- `REACHED_OUT`: When attorney has contacted the lead

**Response:** Updated lead object

#### Download Resume
**GET** `/leads/{lead_uuid}/resume`

Download a lead's resume file.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** File download with appropriate headers

### User Management (Admin Only)

#### Create User
**POST** `/users/`

Create a new user (admin only).

**Headers:**
```
Authorization: Bearer <admin-token>
```

**Request:**
- `email` (string): User email
- `password` (string): User password
- `role` (string): User role ("ATTORNEY" or "ADMIN")

**Response:**
```json
{
  "id": 2,
  "email": "attorney@example.com",
  "role": "ATTORNEY",
  "is_active": true,
  "created_at": "2025-09-26T19:42:27.248539",
  "updated_at": "2025-09-26T19:42:27.248544"
}
```

### Failed Email Management (Admin Only)

#### Get Failed Emails
**GET** `/admin/failed-emails/`

Get all failed email notifications.

**Headers:**
```
Authorization: Bearer <admin-token>
```

**Response:**
```json
[
  {
    "id": 1,
    "lead_id": 5,
    "lead_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "lead_name": "John Doe",
    "lead_email": "john@example.com",
    "attorney_emails": ["attorney1@law.com", "attorney2@law.com"],
    "error_message": "SMTPAuthenticationError: (535, '5.7.8 Username and Password not accepted')",
    "status": "FAILED",
    "created_at": "2025-09-26T14:09:27.248539"
  }
]
```

#### Resend Failed Email
**POST** `/admin/failed-emails/{failed_email_id}/resend`

Resend a failed email notification.

**Headers:**
```
Authorization: Bearer <admin-token>
```

**Response:**
```json
{
  "message": "Email sent successfully and removed from failed emails"
}
```

#### Delete Failed Email
**DELETE** `/admin/failed-emails/{failed_email_id}`

Delete a failed email record.

**Headers:**
```
Authorization: Bearer <admin-token>
```

**Response:**
```json
{
  "message": "Failed email record deleted successfully"
}
```

## Security Features

### Rate Limiting
- Lead submissions: 5 per minute per IP
- Prevents spam and abuse

### File Validation
- Allowed file types: PDF, DOC, DOCX, TXT, RTF
- Maximum file size: 10MB
- Filename security checks

### Authentication
- JWT tokens with 30-minute expiration
- Argon2 password hashing
- Role-based access control

### Data Protection
- UUID-based lead identification (no sequential IDs)
- S3 file storage with IAM access control
- Email validation and duplicate prevention

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "detail": "Invalid email format"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**403 Forbidden:**
```json
{
  "detail": "Not enough permissions. Admin role required."
}
```

**404 Not Found:**
```json
{
  "detail": "Lead not found"
}
```

**429 Too Many Requests:**
```json
{
  "detail": "Too many requests. Please try again later."
}
```

## Database Schema

### Leads Table
- `id`: Primary key (internal)
- `uuid`: Public identifier
- `first_name`, `last_name`, `email`: Lead information
- `resume_path`: S3 URL (internal)
- `status`: PENDING or REACHED_OUT
- `created_at`, `updated_at`: Timestamps

### Users Table
- `id`: Primary key
- `email`: Unique email address
- `hashed_password`: Argon2 hash
- `role`: ATTORNEY or ADMIN
- `is_active`: Account status
- `created_at`, `updated_at`: Timestamps

### Failed Emails Table
- `id`: Primary key
- `lead_id`: Foreign key to leads
- `lead_uuid`: Lead UUID for easy access
- `lead_name`, `lead_email`: Lead information
- `attorney_emails`: JSON array of attorney emails
- `error_message`: Error details
- `status`: FAILED, SENT, or PENDING
- `created_at`, `updated_at`: Timestamps

## Development

### Running Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Testing
```bash
# Start server
uvicorn app.main:app --reload

# Test endpoints
curl -X POST "http://localhost:8000/leads/" \
  -F "first_name=John" \
  -F "last_name=Doe" \
  -F "email=john@example.com" \
  -F "resume=@resume.pdf"
```

## Architecture Decisions

The basic architecture of the application FastAPI as the backend/API layer, PostgresDB as the database, and S3 for remote file storage. Certain decisions were made in the process of development.

### UUID vs Integer IDs
- **UUIDs for public APIs**: Prevents enumeration attacks
- **Integer IDs for internal use**: Better database performance
- **Security by design**: No predictable lead identifiers

### Email Failure Handling
- **Separated concerns**: Lead confirmation vs attorney notifications
- **Failure tracking**: Only critical emails (attorney notifications) tracked
- **Recovery system**: Admins can resend failed emails
- **Spam protection**: Rate limiting prevents abuse

### File Storage
- **AWS S3**: Scalable cloud storage
- **UUID filenames**: Prevents filename conflicts and enumeration
- **Protected access**: Files only accessible via authenticated API
- **No public URLs**: S3 URLs never exposed to clients

### Authentication Strategy
- **JWT tokens**: Stateless authentication
- **Role-based access**: Admin vs Attorney permissions
- **Argon2 hashing**: Modern, secure password hashing
- **Token expiration**: 30-minute default lifetime

## Other Decisions and Future Improvements
- **Database Migration**: Using alembic allows devs to track their database changes and gives the ability to rollback quickly. This is for future-proofing and at least somewhat mitigating the risk of permanent migration errors.
- **Email Services**: The application is sending mail from the app, rather than using a third-party service, for simplicity and cost. The app currently handles retry logic using exponential backoff. However, in a production setting, this is likely to need either a separate service to potentially handle volume, or an asynchronous handler that can send the emails without getting throttled by other services, since it would likely be acceptable that the emails are sent with a slight delay.
- **Email Failure Tracking**: The current implementation is concerned only with resending emails not being sent to attorneys, since the public facing API could flood bad email addresses. However, having some kind of metric or signal indicating that emails fail to send to prospects would be useful, so that a human can notify them directly.
- **File Security Validation**: The application handles simple cases like preventing files that are too large or are not of a proper common format for a resume/CV. Possible updates could include checking for and scrubbing malware in the files.
- **Testing**: Due to time constraints on this assignment, there are no integration tests. Testing was conducted manually using a local environment. In a production setting, unit and integration tests would be added.
