from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    college = Column(String, nullable=False)
    branch = Column(String, nullable=False)
    batch_year = Column(Integer, nullable=False)
    cgpa = Column(Float, nullable=True)
    backlogs = Column(Integer, default=0)

    # e.g. "placed", "interviewing", "eligible", "not_eligible"
    placement_status = Column(String, default="eligible")
    placed_company = Column(String, nullable=True)
    placed_ctc = Column(String, nullable=True)

    resume_path = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="student_profile")
    attendance_records = relationship("AttendanceRecord", back_populates="student")
    assessment_results = relationship("AssessmentResult", back_populates="student")
    interviews = relationship("Interview", back_populates="student")

    @property
    def name(self):
        return self.user.name if self.user else "Unknown"

    @property
    def email(self):
        return self.user.email if self.user else ""

    @property
    def attendance(self):
        """Calculate attendance percentage from records."""
        if not self.attendance_records:
            return 0
        total = len(self.attendance_records)
        present = sum(1 for r in self.attendance_records if r.status == "present")
        return round((present / total) * 100, 1) if total > 0 else 0
