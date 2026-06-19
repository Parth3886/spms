from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
from auth_utils import require_login, require_role
from models.interview import Interview
from models.student import Student
from models.drive import Drive
from models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="../frontend_PlaceTrack")


# ── List interviews (HTML) ────────────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
def list_interviews(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    interviews = (
        db.query(Interview)
        .order_by(Interview.interview_date.desc())
        .all()
    )
    students = db.query(Student).join(User).order_by(User.first_name).all()
    drives = db.query(Drive).filter(Drive.status != "closed").order_by(Drive.company_name).all()

    return templates.TemplateResponse("interviews.html", {
        "request": request,
        "current_user": current_user,
        "interviews": interviews,
        "students": students,
        "drives": drives,
    })


# ── Feedback history (HTML) ───────────────────────────────────────────────────
@router.get("/feedback", response_class=HTMLResponse)
def feedback_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    interviews = (
        db.query(Interview)
        .filter(Interview.result != "pending")
        .order_by(Interview.interview_date.desc())
        .all()
    )
    return templates.TemplateResponse("feedback.html", {
        "request": request,
        "current_user": current_user,
        "interviews": interviews,
    })


# ── Schedule an interview round ───────────────────────────────────────────────
@router.post("/create")
def create_interview(
    student_id: int = Form(...),
    drive_id: int = Form(...),
    round_number: int = Form(1),
    round_type: str = Form("technical"),
    interview_date: date = Form(None),
    interviewer_name: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    drive = db.query(Drive).filter(Drive.id == drive_id).first()
    if not student or not drive:
        raise HTTPException(status_code=404, detail="Student or Drive not found")

    interview = Interview(
        student_id=student_id,
        drive_id=drive_id,
        round_number=round_number,
        round_type=round_type,
        interview_date=interview_date,
        interviewer_name=interviewer_name,
        result="pending",
    )
    db.add(interview)
    student.placement_status = "interviewing"
    db.commit()
    return RedirectResponse("/interviews", status_code=302)


# ── Submit feedback for an interview round ────────────────────────────────────
@router.post("/{interview_id}/feedback")
def submit_feedback(
    interview_id: int,
    result: str = Form(...),
    feedback: str = Form(None),
    rating: int = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    interview.result = result
    interview.feedback = feedback
    interview.rating = rating

    if result == "cleared":
        pending = (
            db.query(Interview)
            .filter(
                Interview.student_id == interview.student_id,
                Interview.drive_id == interview.drive_id,
                Interview.result == "pending",
                Interview.id != interview_id,
            )
            .count()
        )
        if pending == 0:
            interview.student.placement_status = "placed"
            interview.student.placed_company = interview.drive.company_name
    elif result == "rejected":
        interview.student.placement_status = "eligible"

    db.commit()
    return RedirectResponse("/interviews", status_code=302)


# ── Get all interviews for a student (JSON API) ───────────────────────────────
@router.get("/student/{student_id}")
def get_student_interviews(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    interviews = (
        db.query(Interview)
        .filter(Interview.student_id == student_id)
        .order_by(Interview.interview_date)
        .all()
    )
    return [
        {
            "id": i.id,
            "company": i.drive.company_name,
            "role": i.drive.role,
            "round": i.round_number,
            "round_type": i.round_type,
            "date": str(i.interview_date) if i.interview_date else None,
            "result": i.result,
            "feedback": i.feedback,
            "rating": i.rating,
        }
        for i in interviews
    ]
