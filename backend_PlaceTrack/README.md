# Student Placement Management System — PlaceTrack

A FastAPI application with JWT authentication for managing students, placement drives, assessments, attendance, and interview feedback.

## Project Structure

```
PlaceTrack/
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── database.py           # SQLAlchemy DB config (SQLite default)
│   ├── auth_utils.py         # JWT helpers, password hashing, role guards
│   ├── requirements.txt
│   ├── models/
│   │   ├── user.py           # User (admin / trainer / student)
│   │   ├── student.py        # Student profile
│   │   ├── drive.py          # Placement drive
│   │   ├── assessment.py     # Assessment + results
│   │   ├── attendance.py     # Attendance records
│   │   └── interview.py      # Interview rounds & feedback
│   ├── routers/
│   │   ├── auth.py           # /login  /signup  /logout  /  (dashboard)
│   │   ├── students.py       # /students  CRUD
│   │   ├── drives.py         # /create  /update/:id  /delete/:id
│   │   ├── assessments.py    # /assessments  CRUD + results
│   │   ├── attendance.py     # /attendance  mark + view
│   │   └── interviews.py     # /interviews  schedule + feedback
│   ├── static/
│   │   └── uploads/          # Uploaded resumes, JDs, attachments
│   └── templates/            # Jinja2 HTML templates (from frontend/)
│
└── frontend/
    ├── login.html
    ├── signup.html
    ├── index.html            # Dashboard
    ├── create.html           # Add placement drive
    └── update.html           # Edit placement drive
```

## Quick Start

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Copy frontend templates into backend
```bash
cp ../frontend/*.html templates/
```

### 3. Run the server
```bash
uvicorn main:app --reload --port 8000
```

### 4. Open in browser
```
http://localhost:8000/signup   →  Create your first admin account
http://localhost:8000/login    →  Sign in
http://localhost:8000/         →  Dashboard
http://localhost:8000/docs     →  Swagger API docs
```

## Roles & Permissions

| Feature               | Admin | Trainer | Student |
|-----------------------|-------|---------|---------|
| View dashboard        | ✅    | ✅      | ✅      |
| Add/edit students     | ✅    | ✅      | ❌      |
| Delete students       | ✅    | ❌      | ❌      |
| Schedule drives       | ✅    | ✅      | ❌      |
| Mark attendance       | ✅    | ✅      | ❌      |
| Create assessments    | ✅    | ✅      | ❌      |
| Submit interview feedback | ✅ | ✅     | ❌      |
| View own profile      | ✅    | ✅      | ✅      |

## Switch to PostgreSQL

In `database.py`, replace:
```python
DATABASE_URL = "sqlite:///./placetrack.db"
```
with:
```python
DATABASE_URL = "postgresql://user:password@localhost/placetrack"
```
And remove `connect_args={"check_same_thread": False}` from `create_engine`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/login` | Login with role selector |
| GET/POST | `/signup` | Register student or trainer |
| GET | `/logout` | Clear session cookie |
| GET | `/` | Dashboard (requires login) |
| GET/POST | `/students/create` | Add student |
| GET/POST | `/students/update/{id}` | Edit student |
| GET | `/students/delete/{id}` | Delete student |
| GET/POST | `/create` | Schedule placement drive |
| GET/POST | `/update/{id}` | Edit drive |
| GET | `/delete/{id}` | Delete drive |
| GET | `/assessments/` | List assessments |
| POST | `/assessments/create` | Create assessment |
| POST | `/assessments/{id}/results` | Submit student score |
| POST | `/attendance/mark` | Mark attendance |
| GET | `/attendance/student/{id}` | Student attendance report |
| POST | `/interviews/create` | Schedule interview round |
| POST | `/interviews/{id}/feedback` | Submit feedback |
