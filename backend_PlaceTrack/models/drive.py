from sqlalchemy import Column, Integer, String, Date, Float, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Drive(Base):
    __tablename__ = "drives"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    sector = Column(String, nullable=True)
    role = Column(String, nullable=False)
    ctc = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    drive_type = Column(String, default="on-campus")  # on-campus / off-campus / virtual
    drive_date = Column(Date, nullable=False)
    reg_deadline = Column(Date, nullable=True)
    vacancies = Column(Integer, nullable=True)

    min_cgpa = Column(Float, default=0.0)
    max_backlogs = Column(Integer, default=0)
    eligible_branches = Column(String, default="CS,IT")  # comma-separated

    status = Column(String, default="upcoming")  # upcoming / open / closed
    attachment = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    interviews = relationship("Interview", back_populates="drive")

    @property
    def branches(self):
        return self.eligible_branches.split(",") if self.eligible_branches else []
