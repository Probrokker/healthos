"""
FastAPI — REST API для Next.js дашборда.
Запускается параллельно с ботом или отдельным сервисом.
"""
import os
import sys
from datetime import date, datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "services"))

from models.database import SessionLocal, Profile, LabResult, DoctorVisit, Medication, GrowthRecord, Vaccine, Hypothesis, create_tables
from agents.base_agent import calculate_age
from services.context_builder import get_labs_trend

app = FastAPI(title="Health-OS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# === SCHEMAS ===

class ProfileOut(BaseModel):
    id: int
    name: str
    birthdate: date
    gender: Optional[str]
    blood_type: Optional[str]
    is_child: bool
    allergies: Optional[list]
    chronic_conditions: Optional[list]
    age_years: int
    age_months: int

    class Config:
        from_attributes = True


class LabMarker(BaseModel):
    name: str
    value: str
    unit: Optional[str]
    ref_min: Optional[str]
    ref_max: Optional[str]
    status: Optional[str]


class LabResultOut(BaseModel):
    id: int
    profile_id: int
    date: date
    lab_name: Optional[str]
    test_type: Optional[str]
    markers: Optional[list]

    class Config:
        from_attributes = True


class DoctorVisitOut(BaseModel):
    id: int
    profile_id: int
    date: date
    doctor_name: Optional[str]
    specialty: Optional[str]
    diagnosis: Optional[str]
    recommendations: Optional[str]

    class Config:
        from_attributes = True


class GrowthRecordOut(BaseModel):
    id: int
    profile_id: int
    date: date
    height_cm: Optional[float]
    weight_kg: Optional[float]
    bmi: Optional[float]
    height_percentile: Optional[float]
    weight_percentile: Optional[float]

    class Config:
        from_attributes = True


class MedicationOut(BaseModel):
    id: int
    profile_id: int
    name: str
    dosage: Optional[str]
    frequency: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    is_active: bool
    reason: Optional[str]

    class Config:
        from_attributes = True


# === ENDPOINTS ===

@app.get("/")
def root():
    return {"status": "Health-OS API running", "version": "1.0.0"}


@app.get("/profiles", response_model=List[ProfileOut])
def get_profiles(db: Session = Depends(get_db)):
    profiles = db.query(Profile).all()
    result = []
    for p in profiles:
        age = calculate_age(p.birthdate)
        result.append(ProfileOut(
            id=p.id,
            name=p.name,
            birthdate=p.birthdate,
            gender=p.gender,
            blood_type=p.blood_type,
            is_child=p.is_child,
            allergies=p.allergies or [],
            chronic_conditions=p.chronic_conditions or [],
            age_years=age["years"],
            age_months=age["months"],
        ))
    return result


@app.get("/profiles/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    p = db.query(Profile).filter(Profile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Профиль не найден")
    age = calculate_age(p.birthdate)
    return ProfileOut(
        id=p.id,
        name=p.name,
        birthdate=p.birthdate,
        gender=p.gender,
        blood_type=p.blood_type,
        is_child=p.is_child,
        allergies=p.allergies or [],
        chronic_conditions=p.chronic_conditions or [],
        age_years=age["years"],
        age_months=age["months"],
    )


@app.get("/profiles/{profile_id}/labs", response_model=List[LabResultOut])
def get_labs(
    profile_id: int,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    labs = db.query(LabResult).filter(
        LabResult.profile_id == profile_id
    ).order_by(LabResult.date.desc()).limit(limit).all()
    return labs


@app.get("/profiles/{profile_id}/labs/trend")
def get_marker_trend(
    profile_id: int,
    marker: str = Query(..., description="Название показателя"),
    db: Session = Depends(get_db)
):
    trend = get_labs_trend(db, profile_id, marker)
    return {"marker": marker, "trend": trend}


@app.get("/profiles/{profile_id}/visits", response_model=List[DoctorVisitOut])
def get_visits(
    profile_id: int,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    visits = db.query(DoctorVisit).filter(
        DoctorVisit.profile_id == profile_id
    ).order_by(DoctorVisit.date.desc()).limit(limit).all()
    return visits


@app.get("/profiles/{profile_id}/growth", response_model=List[GrowthRecordOut])
def get_growth(
    profile_id: int,
    db: Session = Depends(get_db)
):
    records = db.query(GrowthRecord).filter(
        GrowthRecord.profile_id == profile_id
    ).order_by(GrowthRecord.date.asc()).all()
    return records


@app.get("/profiles/{profile_id}/medications", response_model=List[MedicationOut])
def get_medications(
    profile_id: int,
    active_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    query = db.query(Medication).filter(Medication.profile_id == profile_id)
    if active_only:
        query = query.filter(Medication.is_active == True)
    return query.order_by(Medication.start_date.desc()).all()


@app.get("/profiles/{profile_id}/stats")
def get_stats(profile_id: int, db: Session = Depends(get_db)):
    """Сводная статистика профиля для дашборда."""
    p = db.query(Profile).filter(Profile.id == profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    labs_count = db.query(LabResult).filter(LabResult.profile_id == profile_id).count()
    visits_count = db.query(DoctorVisit).filter(DoctorVisit.profile_id == profile_id).count()
    active_meds = db.query(Medication).filter(
        Medication.profile_id == profile_id, Medication.is_active == True
    ).count()

    # Последний анализ
    last_lab = db.query(LabResult).filter(
        LabResult.profile_id == profile_id
    ).order_by(LabResult.date.desc()).first()

    # Аномальные показатели в последних анализах
    recent_labs = db.query(LabResult).filter(
        LabResult.profile_id == profile_id
    ).order_by(LabResult.date.desc()).limit(5).all()

    abnormal_count = 0
    for lab in recent_labs:
        for marker in (lab.markers or []):
            if marker.get("status") not in ("normal", None):
                abnormal_count += 1

    return {
        "labs_count": labs_count,
        "visits_count": visits_count,
        "active_medications": active_meds,
        "last_lab_date": last_lab.date.isoformat() if last_lab else None,
        "last_lab_type": last_lab.test_type if last_lab else None,
        "recent_abnormal_markers": abnormal_count,
    }


@app.get("/family/overview")
def get_family_overview(db: Session = Depends(get_db)):
    """Обзор всей семьи для главного экрана дашборда."""
    profiles = db.query(Profile).all()
    result = []
    for p in profiles:
        age = calculate_age(p.birthdate)
        labs_count = db.query(LabResult).filter(LabResult.profile_id == p.id).count()
        active_meds = db.query(Medication).filter(
            Medication.profile_id == p.id, Medication.is_active == True
        ).count()
        last_visit = db.query(DoctorVisit).filter(
            DoctorVisit.profile_id == p.id
        ).order_by(DoctorVisit.date.desc()).first()

        result.append({
            "id": p.id,
            "name": p.name,
            "is_child": p.is_child,
            "age_years": age["years"],
            "age_months": age["months"],
            "labs_count": labs_count,
            "active_medications": active_meds,
            "last_visit_date": last_visit.date.isoformat() if last_visit else None,
            "last_visit_specialty": last_visit.specialty if last_visit else None,
        })

    return {"family": result, "total_members": len(result)}



class ProfileCreate(BaseModel):
    name: str
    birthdate: date
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    is_child: bool = True
    allergies: Optional[list] = None
    chronic_conditions: Optional[list] = None
    family_history: Optional[dict] = None
    notes: Optional[str] = None


@app.post("/profiles", response_model=ProfileOut)
def create_profile(data: ProfileCreate, db: Session = Depends(get_db)):
    age = calculate_age(data.birthdate)
    p = Profile(
        name=data.name,
        birthdate=data.birthdate,
        gender=data.gender,
        blood_type=data.blood_type,
        is_child=data.is_child,
        allergies=data.allergies or [],
        chronic_conditions=data.chronic_conditions or [],
        family_history=data.family_history or {},
        notes=data.notes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return ProfileOut(
        id=p.id, name=p.name, birthdate=p.birthdate,
        gender=p.gender, blood_type=p.blood_type, is_child=p.is_child,
        allergies=p.allergies or [], chronic_conditions=p.chronic_conditions or [],
        age_years=age["years"], age_months=age["months"],
    )

if __name__ == "__main__":
    import uvicorn
    create_tables()
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("API_PORT", 8000)))
