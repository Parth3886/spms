from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date

from database import get_db
from auth_utils import require_login, require_role
from models.assessment import Assessment, AssessmentResult
from models.student import Student
from models.user import User

router = APIRouter()
templates = Jinja2Templates(directory="../frontend_PlaceTrack")


# ── Create assessment ─────────────────────────────────────────────────────────
@router.post("/create")
def create_assessment(
    title: str = Form(...),
    subject: str = Form(...),
    total_marks: int = Form(100),
    assessment_date: date = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    assessment = Assessment(
        title=title,
        subject=subject,
        total_marks=total_marks,
        date=assessment_date,
        description=description,
        created_by=current_user.id,
    )
    db.add(assessment)
    db.commit()
    return RedirectResponse("/assessments", status_code=302)


# ── List assessments (HTML) ───────────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse)
def list_assessments(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    assessments = db.query(Assessment).order_by(Assessment.date.desc()).all()
    return templates.TemplateResponse("assessments.html", {
        "request": request,
        "current_user": current_user,
        "assessments": assessments,
    })


# ── List assessments (JSON API) ────────────────────────────────────────────────
@router.get("/api")
def list_assessments_json(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    assessments = db.query(Assessment).order_by(Assessment.date.desc()).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "subject": a.subject,
            "total_marks": a.total_marks,
            "date": str(a.date) if a.date else None,
            "avg_score": a.avg_score,
            "submissions": len(a.results),
        }
        for a in assessments
    ]


# ── Get results for an assessment (HTML) ──────────────────────────────────────
@router.get("/{assessment_id}/results", response_class=HTMLResponse)
def get_results_page(
    assessment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    students = db.query(Student).join(User).order_by(User.first_name).all()
    results = db.query(AssessmentResult).filter(AssessmentResult.assessment_id == assessment_id).all()
    
    score_map = {r.student_id: r.score for r in results}
    remarks_map = {r.student_id: r.remarks for r in results}

    return templates.TemplateResponse("assessment_results.html", {
        "request": request,
        "current_user": current_user,
        "assessment": assessment,
        "students": students,
        "score_map": score_map,
        "remarks_map": remarks_map,
        "round": round,
    })


# ── Submit / update results for an assessment (Bulk Form POST) ────────────────
@router.post("/{assessment_id}/results")
async def submit_results_bulk(
    assessment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "trainer")),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    form_data = await request.form()
    
    for key, val in form_data.items():
        if key.startswith("score_"):
            student_id = int(key.split("_")[1])
            score_str = val.strip()
            remark = form_data.get(f"remarks_{student_id}", "").strip()
            
            if score_str == "":
                existing = db.query(AssessmentResult).filter_by(assessment_id=assessment_id, student_id=student_id).first()
                if existing:
                    db.delete(existing)
                continue

            try:
                score = float(score_str)
            except ValueError:
                continue

            existing = db.query(AssessmentResult).filter_by(assessment_id=assessment_id, student_id=student_id).first()
            if existing:
                existing.score = score
                existing.remarks = remark
            else:
                result = AssessmentResult(
                    assessment_id=assessment_id,
                    student_id=student_id,
                    score=score,
                    remarks=remark,
                )
                db.add(result)

    db.commit()
    return RedirectResponse(f"/assessments/{assessment_id}/results", status_code=302)


# ── Delete assessment ─────────────────────────────────────────────────────────
@router.delete("/{assessment_id}")
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(assessment)
    db.commit()
    return JSONResponse({"status": "deleted"})
