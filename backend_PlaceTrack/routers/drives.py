import os, shutil
from datetime import date
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from auth_utils import require_login, require_role
from models.drive import Drive
from models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="../frontend_PlaceTrack")
UPLOAD_DIR = "static/uploads"


# ── List drives (HTML) ────────────────────────────────────────────────────────
@router.get("/drives", response_class=HTMLResponse)
def list_drives(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    drives = db.query(Drive).order_by(Drive.drive_date.desc()).all()
    return templates.TemplateResponse("drives.html", {
        "request": request,
        "current_user": current_user,
        "drives": drives,
    })


# ── Create drive ──────────────────────────────────────────────────────────────
@router.get("/create", response_class=HTMLResponse)
def create_drive_page(
    request: Request,
    current_user: User = Depends(require_role("admin", "trainer")),
):
    return templates.TemplateResponse("drive_create.html", {
        "request": request,
        "current_user": current_user,
    })


@router.post("/create")
def create_drive(
    request: Request,
    company_name: str = Form(...),
    sector: str = Form(None),
    role: str = Form(...),
    ctc: str = Form(None),
    description: str = Form(None),
    drive_type: str = Form("on-campus"),
    drive_date: date = Form(...),
    reg_deadline: date = Form(None),
    vacancies: int = Form(None),
    min_cgpa: float = Form(0.0),
    max_backlogs: int = Form(0),
    branches: list[str] = Form(default=[]),
    attachment: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    attach_path = None
    if attachment and attachment.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        safe_name = f"drive_{company_name.replace(' ', '_')}_{attachment.filename}"
        dest = os.path.join(UPLOAD_DIR, safe_name)
        with open(dest, "wb") as f:
            shutil.copyfileobj(attachment.file, f)
        attach_path = safe_name

    drive = Drive(
        company_name=company_name,
        sector=sector,
        role=role,
        ctc=ctc,
        description=description,
        drive_type=drive_type,
        drive_date=drive_date,
        reg_deadline=reg_deadline,
        vacancies=vacancies,
        min_cgpa=min_cgpa,
        max_backlogs=max_backlogs,
        eligible_branches=",".join(branches) if branches else "ALL",
        status="upcoming",
        attachment=attach_path,
    )
    db.add(drive)
    db.commit()
    return RedirectResponse("/drives", status_code=302)


# ── Update drive ──────────────────────────────────────────────────────────────
@router.get("/update/{drive_id}", response_class=HTMLResponse)
def update_drive_page(
    drive_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    drive = db.query(Drive).filter(Drive.id == drive_id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    return templates.TemplateResponse("drive_update.html", {
        "request": request,
        "current_user": current_user,
        "drive": drive,
    })


@router.post("/update/{drive_id}")
def update_drive(
    drive_id: int,
    request: Request,
    company_name: str = Form(...),
    sector: str = Form(None),
    role: str = Form(...),
    ctc: str = Form(None),
    description: str = Form(None),
    drive_date: date = Form(...),
    reg_deadline: date = Form(None),
    vacancies: int = Form(None),
    min_cgpa: float = Form(0.0),
    max_backlogs: int = Form(0),
    branches: list[str] = Form(default=[]),
    status: str = Form("upcoming"),
    attachment: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    drive = db.query(Drive).filter(Drive.id == drive_id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    drive.company_name = company_name
    drive.sector = sector
    drive.role = role
    drive.ctc = ctc
    drive.description = description
    drive.drive_date = drive_date
    drive.reg_deadline = reg_deadline
    drive.vacancies = vacancies
    drive.min_cgpa = min_cgpa
    drive.max_backlogs = max_backlogs
    drive.eligible_branches = ",".join(branches) if branches else "ALL"
    drive.status = status

    if attachment and attachment.filename:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        safe_name = f"drive_{drive.id}_{attachment.filename}"
        dest = os.path.join(UPLOAD_DIR, safe_name)
        with open(dest, "wb") as f:
            shutil.copyfileobj(attachment.file, f)
        drive.attachment = safe_name

    db.commit()
    return RedirectResponse("/drives", status_code=302)


# ── Delete drive ──────────────────────────────────────────────────────────────
@router.get("/delete/{drive_id}")
def delete_drive(
    drive_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    drive = db.query(Drive).filter(Drive.id == drive_id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    db.delete(drive)
    db.commit()
    return RedirectResponse("/drives", status_code=302)


# ── List drives (JSON API) ────────────────────────────────────────────────────
@router.get("/drives/api")
def list_drives_api(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    drives = db.query(Drive).order_by(Drive.drive_date).all()
    return [
        {
            "id": d.id,
            "company": d.company_name,
            "role": d.role,
            "ctc": d.ctc,
            "date": str(d.drive_date),
            "status": d.status,
            "vacancies": d.vacancies,
        }
        for d in drives
    ]
