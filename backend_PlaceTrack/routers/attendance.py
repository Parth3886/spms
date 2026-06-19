from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
from auth_utils import require_login, require_role
from models.attendance import AttendanceRecord
from models.student import Student
from models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="../frontend_PlaceTrack")


# ── View & Mark Attendance (HTML) ─────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
def list_attendance(
    request: Request,
    attendance_date: date = None,
    session: str = "morning",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    if not attendance_date:
        attendance_date = date.today()

    students = db.query(Student).join(User).order_by(User.first_name).all()
    records = db.query(AttendanceRecord).filter_by(date=attendance_date, session=session).all()
    
    status_map = {r.student_id: r.status for r in records}

    return templates.TemplateResponse("attendance.html", {
        "request": request,
        "current_user": current_user,
        "students": students,
        "attendance_date": str(attendance_date),
        "session": session,
        "status_map": status_map,
    })


# ── Mark attendance (bulk Form POST) ──────────────────────────────────────────
@router.post("/mark")
async def mark_attendance(
    request: Request,
    attendance_date: date = Form(...),
    session: str = Form("morning"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    form_data = await request.form()
    
    for key, val in form_data.items():
        if key.startswith("status_"):
            student_id = int(key.split("_")[1])
            status = val.strip()

            existing = db.query(AttendanceRecord).filter_by(
                student_id=student_id,
                date=attendance_date,
                session=session,
            ).first()

            if existing:
                existing.status = status
            else:
                rec = AttendanceRecord(
                    student_id=student_id,
                    date=attendance_date,
                    status=status,
                    session=session,
                    marked_by=current_user.id,
                )
                db.add(rec)
                
    db.commit()
    return RedirectResponse(f"/attendance?attendance_date={attendance_date}&session={session}", status_code=302)


# ── Get attendance for a student (JSON API) ───────────────────────────────────
@router.get("/student/{student_id}")
def get_student_attendance(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.student_id == student_id)
        .order_by(AttendanceRecord.date.desc())
        .all()
    )
    return {
        "student_id": student_id,
        "student_name": student.name,
        "attendance_percentage": student.attendance,
        "total_records": len(records),
        "present": sum(1 for r in records if r.status == "present"),
        "absent": sum(1 for r in records if r.status == "absent"),
        "records": [
            {"date": str(r.date), "status": r.status, "session": r.session}
            for r in records
        ],
    }


# ── Get attendance for a date (JSON API) ──────────────────────────────────────
@router.get("/date/{attendance_date}")
def get_date_attendance(
    attendance_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.date == attendance_date)
        .all()
    )
    return [
        {
            "student_id": r.student_id,
            "student_name": r.student.name,
            "status": r.status,
            "session": r.session,
        }
        for r in records
    ]
