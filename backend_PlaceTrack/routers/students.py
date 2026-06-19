import os, shutil
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from auth_utils import require_login, require_role
from models.student import Student
from models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="../frontend_PlaceTrack")
UPLOAD_DIR = "static/uploads"


# ── List students (HTML) ──────────────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
def list_students(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    students = db.query(Student).join(User).order_by(Student.created_at.desc()).all()
    return templates.TemplateResponse("students.html", {
        "request": request,
        "current_user": current_user,
        "students": students,
    })


# ── Create student form ───────────────────────────────────────────────────────
@router.get("/create", response_class=HTMLResponse)
def create_student_page(
    request: Request,
    current_user: User = Depends(require_role("admin", "trainer")),
):
    return templates.TemplateResponse("student_create.html", {
        "request": request,
        "current_user": current_user,
    })


@router.post("/create")
def create_student(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    college: str = Form(...),
    branch: str = Form(...),
    batch_year: int = Form(...),
    cgpa: float = Form(None),
    backlogs: int = Form(0),
    resume: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse("student_create.html", {
            "request": request,
            "current_user": current_user,
            "error": "A user with this email already exists.",
        })

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        hashed_password="",  # Placeholder — student can set via reset
        role="student",
    )
    db.add(user)
    db.flush()

    resume_path = None
    if resume and resume.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        safe_name = f"resume_{user.id}_{resume.filename}"
        dest = os.path.join(UPLOAD_DIR, safe_name)
        with open(dest, "wb") as f:
            shutil.copyfileobj(resume.file, f)
        resume_path = safe_name

    student = Student(
        user_id=user.id,
        college=college,
        branch=branch,
        batch_year=batch_year,
        cgpa=cgpa,
        backlogs=backlogs,
        resume_path=resume_path,
    )
    db.add(student)
    db.commit()
    return RedirectResponse("/students", status_code=302)


# ── Update student ────────────────────────────────────────────────────────────
@router.get("/update/{student_id}", response_class=HTMLResponse)
def update_student_page(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return templates.TemplateResponse("student_update.html", {
        "request": request,
        "current_user": current_user,
        "student": student,
    })


@router.post("/update/{student_id}")
def update_student(
    student_id: int,
    request: Request,
    college: str = Form(...),
    branch: str = Form(...),
    batch_year: int = Form(...),
    cgpa: float = Form(None),
    backlogs: int = Form(0),
    placement_status: str = Form("eligible"),
    placed_company: str = Form(None),
    placed_ctc: str = Form(None),
    resume: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.college = college
    student.branch = branch
    student.batch_year = batch_year
    student.cgpa = cgpa
    student.backlogs = backlogs
    student.placement_status = placement_status
    student.placed_company = placed_company if placement_status == "placed" else None
    student.placed_ctc = placed_ctc if placement_status == "placed" else None

    if resume and resume.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        safe_name = f"resume_{student.id}_{resume.filename}"
        dest = os.path.join(UPLOAD_DIR, safe_name)
        with open(dest, "wb") as f:
            shutil.copyfileobj(resume.file, f)
        student.resume_path = safe_name

    db.commit()
    return RedirectResponse("/students", status_code=302)


# ── Delete student ────────────────────────────────────────────────────────────
@router.get("/delete/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return RedirectResponse("/students", status_code=302)
