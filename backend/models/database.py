from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/healthos")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    birthdate = Column(Date, nullable=False)
    blood_type = Column(String(10))
    gender = Column(String(10))
    is_child = Column(Boolean, default=True)
    allergies = Column(JSON, default=list)
    chronic_conditions = Column(JSON, default=list)
    family_history = Column(JSON, default=dict)
    current_doctor = Column(String(200))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    labs = relationship("LabResult", back_populates="profile", cascade="all, delete-orphan")
    visits = relationship("DoctorVisit", back_populates="profile", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="profile", cascade="all, delete-orphan")
    growth_records = relationship("GrowthRecord", back_populates="profile", cascade="all, delete-orphan")
    vaccines = relationship("Vaccine", back_populates="profile", cascade="all, delete-orphan")


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    date = Column(Date, nullable=False)
    lab_name = Column(String(200))
    test_type = Column(String(100))
    markers = Column(JSON, default=list)  # [{name, value, unit, ref_min, ref_max, status}]
    raw_text = Column(Text)
    file_path = Column(String(500))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("Profile", back_populates="labs")


class DoctorVisit(Base):
    __tablename__ = "doctor_visits"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    date = Column(Date, nullable=False)
    doctor_name = Column(String(200))
    specialty = Column(String(100))
    clinic = Column(String(200))
    diagnosis = Column(Text)
    prescriptions = Column(JSON, default=list)
    recommendations = Column(Text)
    follow_up_date = Column(Date)
    follow_up_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("Profile", back_populates="visits")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    name = Column(String(200), nullable=False)
    dosage = Column(String(100))
    frequency = Column(String(100))
    start_date = Column(Date)
    end_date = Column(Date)
    is_active = Column(Boolean, default=True)
    prescribed_by = Column(String(200))
    reason = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("Profile", back_populates="medications")


class GrowthRecord(Base):
    __tablename__ = "growth_records"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    date = Column(Date, nullable=False)
    height_cm = Column(Float)
    weight_kg = Column(Float)
    head_circumference_cm = Column(Float)
    bmi = Column(Float)
    height_percentile = Column(Float)
    weight_percentile = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("Profile", back_populates="growth_records")


class Vaccine(Base):
    __tablename__ = "vaccines"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    name = Column(String(200), nullable=False)
    date_given = Column(Date)
    batch_number = Column(String(100))
    clinic = Column(String(200))
    next_dose_date = Column(Date)
    is_completed = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("Profile", back_populates="vaccines")


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="moderate")  # strong, moderate, weak, refuted, confirmed
    evidence_for = Column(JSON, default=list)
    evidence_against = Column(JSON, default=list)
    next_steps = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


def create_tables():
    Base.metadata.create_all(bind=engine)
