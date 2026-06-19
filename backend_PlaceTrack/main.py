from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
import logging
import traceback

from database import engine, Base
from routers import auth, students, drives, assessments, attendance, interviews

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create all DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Student Placement Management System", version="1.0.0")

# Middleware
app.add_middleware(SessionMiddleware, secret_key="CHANGE_THIS_SECRET_KEY_IN_PRODUCTION")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="../frontend_PlaceTrack")

# Include routers
app.include_router(auth.router, tags=["Auth"])
app.include_router(students.router, prefix="/students", tags=["Students"])
app.include_router(drives.router, tags=["Drives"])
app.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])
app.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
app.include_router(interviews.router, prefix="/interviews", tags=["Interviews"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "PlaceTrack API"}


# Global exception handlers for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log all unhandled exceptions with full traceback."""
    error_trace = traceback.format_exc()
    logger.error(f"\n{'='*60}\nUNCHAUGHT EXCEPTION:\n{error_trace}\n{'='*60}\n")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors."""
    logger.error(f"Validation Error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

