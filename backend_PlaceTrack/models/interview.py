from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    drive_id = Column(Integer, ForeignKey("drives.id"), nullable=False)

    round_number = Column(Integer, default=1)
    round_type = Column(String, nullable=True)   # aptitude / technical / hr / gd
    interview_date = Column(Date, nullable=True)

    result = Column(String, default="pending")   # pending / cleared / rejected / on-hold
    feedback = Column(Text, nullable=True)
    interviewer_name = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)       # 1–5

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    student = relationship("Student", back_populates="interviews")
    drive = relationship("Drive", back_populates="interviews")
