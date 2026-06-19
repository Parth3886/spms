from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from collections import defaultdict

from database import get_db
from models.user import User
from auth_utils import (
    hash_password, verify_password,
    create_access_token, get_current_user, require_login,
)

router = APIRouter()
templates = Jinja2Templates(directory="../frontend_PlaceTrack")


# ── Home / dashboard redirect ─────────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    from models.student import Student
    from models.drive import Drive
    from models.assessment import Assessment

    students = (
        db.query(Student)
        .join(User)
        .order_by(Student.created_at.desc())
        .limit(10)
        .all()
    )
    drives = db.query(Drive).filter(Drive.status != "closed").order_by(Drive.drive_date).limit(5).all()
    assessments = db.query(Assessment).order_by(Assessment.created_at.desc()).limit(5).all()

    total_students = db.query(Student).count()
    placed = db.query(Student).filter(Student.placement_status == "placed").count()
    active_drives = db.query(Drive).filter(Drive.status == "open").count()

    stats = {
        "total_students": total_students,
        "placed": placed,
        "placement_rate": round((placed / total_students * 100), 1) if total_students else 0,
        "active_drives": active_drives,
        "pending_assessments": db.query(Assessment).count(),
    }

    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user": user,
        "students": students,
        "drives": drives,
        "assessments": assessments,
        "stats": stats,
    })


# ── Login ─────────────────────────────────────────────────────────────────────
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("student"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email or password.",
        })

    if user.role != role:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"This account is registered as '{user.role}', not '{role}'.",
        })

    token = create_access_token({"sub": str(user.id), "role": user.role})
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 8,   # 8 hours
        samesite="lax",
    )
    return response


# ── Signup ────────────────────────────────────────────────────────────────────
@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})


@router.post("/signup")
def signup_submit(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form("student"),
    college: str = Form(None),
    batch_year: int = Form(None),
    branch: str = Form(None),
    specialization: str = Form(None),
    employee_id: str = Form(None),
    db: Session = Depends(get_db),
):
    if password != confirm_password:
        return templates.TemplateResponse("signup.html", {
            "request": request, "error": "Passwords do not match."
        })

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse("signup.html", {
            "request": request, "error": "An account with this email already exists."
        })

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        specialization=specialization,
        employee_id=employee_id,
    )
    db.add(user)
    db.flush()  # get user.id

    if role == "student":
        from models.student import Student
        student = Student(
            user_id=user.id,
            college=college or "",
            branch=branch or "",
            batch_year=batch_year or 2026,
        )
        db.add(student)

    db.commit()
    return RedirectResponse("/login", status_code=302)


# ── Logout ────────────────────────────────────────────────────────────────────
@router.get("/logout")
def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    return response


# ── Trainers directory ────────────────────────────────────────────────────────
@router.get("/trainers", response_class=HTMLResponse)
def trainers_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_login)):
    trainers = db.query(User).filter(User.role.in_(["trainer", "admin"])).order_by(User.first_name).all()
    return templates.TemplateResponse("trainers.html", {
        "request": request,
        "current_user": current_user,
        "trainers": trainers,
    })


@router.get("/placement")
def placement_redirect():
    return RedirectResponse("/drives", status_code=302)


@router.get("/feedback")
def feedback_redirect():
    return RedirectResponse("/interviews/feedback", status_code=302)


# ── Performance analytics ─────────────────────────────────────────────────────
@router.get("/performance", response_class=HTMLResponse)
def performance_page(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_login)):
    from models.student import Student

    students = db.query(Student).join(User).order_by(User.first_name).all()
    total_students = len(students)
    placed = sum(1 for s in students if s.placement_status == "placed")

    # CGPA & attendance averages
    cgpas = [s.cgpa for s in students if s.cgpa is not None]
    avg_cgpa = round(sum(cgpas) / len(cgpas), 2) if cgpas else 0
    attendances = [s.attendance for s in students]
    avg_attendance = round(sum(attendances) / len(attendances), 1) if attendances else 0

    # Branch-wise placement rate
    branch_data = defaultdict(lambda: {"total": 0, "placed": 0})
    for s in students:
        branch_data[s.branch]["total"] += 1
        if s.placement_status == "placed":
            branch_data[s.branch]["placed"] += 1
    branch_stats = {
        branch: {"total": d["total"], "placed": d["placed"],
                 "rate": round((d["placed"] / d["total"]) * 100, 1) if d["total"] else 0}
        for branch, d in sorted(branch_data.items())
    }

    # Status counts
    status_counts = defaultdict(int)
    for s in students:
        status_counts[s.placement_status] += 1

    stats = {
        "total_students": total_students,
        "placed": placed,
        "placement_rate": round((placed / total_students * 100), 1) if total_students else 0,
        "avg_cgpa": avg_cgpa,
        "avg_attendance": avg_attendance,
    }

    return templates.TemplateResponse("performance.html", {
        "request": request,
        "current_user": current_user,
        "students": students,
        "stats": stats,
        "branch_stats": branch_stats,
        "status_counts": dict(status_counts),
    })
