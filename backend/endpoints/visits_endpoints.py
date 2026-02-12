from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from miniorm.session import Session
from models import Visit, Pet, Vet
from deps import get_session

router = APIRouter()

class VisitCreate(BaseModel):
    pet_id: int
    vet_id: int
    date: str
    reason: str
    paid: int


def _apply_visit_filters(visits, date, reason, paid):
    if date:
        visits = [v for v in visits if v.date and date in (v.date or "")]
    if reason:
        visits = [v for v in visits if v.reason and reason.lower() in (v.reason or "").lower()]
    if paid is not None:
        p = int(paid) if str(paid).isdigit() else paid
        visits = [v for v in visits if v.paid == p]
    return visits

@router.get("/api/visits")
def get_visits(
    session: Session = Depends(get_session),
    owner_id: int = Query(None),
    vet_id: int = Query(None),
    pet_id: int = Query(None),
    date: str = Query(None),
    reason: str = Query(None),
    paid: int = Query(None),
):
    if owner_id is not None:
        pets = session.query(Pet).filter(owner=owner_id).all()
        pet_ids = [p.pet_id for p in pets]
        all_visits = session.query(Visit).all()
        visits = [v for v in all_visits if v.pet and v.pet.pet_id in pet_ids]
    else:
        visits = session.query(Visit).all()
    if vet_id is not None:
        visits = [v for v in visits if v.vet and v.vet.person_id == vet_id]
    if pet_id is not None:
        visits = [v for v in visits if v.pet and v.pet.pet_id == pet_id]
    visits = _apply_visit_filters(visits, date, reason, paid)
    return [
        {
            "visit_id": v.visit_id,
            "pet_id": v.pet.pet_id if v.pet else None,
            "vet_id": v.vet.person_id if v.vet else None,
            "date": v.date,
            "reason": v.reason,
            "paid": v.paid
        }
        for v in visits
    ]

@router.post("/api/visits")
def add_visit(visit: VisitCreate, session: Session = Depends(get_session)):
    pet = session.get(Pet, visit.pet_id)
    vet = session.get(Vet, visit.vet_id)
    new_visit = Visit(
        pet=pet,
        vet=vet,
        date=visit.date,
        reason=visit.reason,
        paid=visit.paid
    )
    session.add(new_visit)
    session.commit()
    return {
        "visit_id": new_visit.visit_id,
        "pet_id": pet.pet_id if pet else None,
        "vet_id": vet.person_id if vet else None,
        "date": new_visit.date,
        "reason": new_visit.reason,
        "paid": new_visit.paid,
            "message": "Visit added successfully"
        }

class VisitUpdate(BaseModel):
    pet_id: int | None = None
    vet_id: int | None = None
    date: str | None = None
    reason: str | None = None
    paid: int | None = None

@router.put("/api/visits/{visit_id}")
def update_visit(visit_id: int, visit: VisitUpdate, session: Session = Depends(get_session)):
    existing = session.get(Visit, visit_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Visit not found")
    if visit.pet_id is not None:
        pet = session.get(Pet, visit.pet_id)
        if not pet:
            raise HTTPException(status_code=404, detail="Pet not found")
        setattr(existing, "pet", pet)
    if visit.vet_id is not None:
        vet = session.get(Vet, visit.vet_id)
        if not vet:
            raise HTTPException(status_code=404, detail="Vet not found")
        setattr(existing, "vet", vet)
    if visit.date is not None:
        setattr(existing, "date", visit.date)
    if visit.reason is not None:
        setattr(existing, "reason", visit.reason)
    if visit.paid is not None:
        setattr(existing, "paid", visit.paid)
    session.update(existing)
    session.commit()
    return {
        "visit_id": existing.visit_id,
        "pet_id": existing.pet.pet_id if existing.pet else None,
        "vet_id": existing.vet.person_id if existing.vet else None,
        "date": existing.date,
        "reason": existing.reason,
        "paid": existing.paid,
        "message": "Visit updated"
    }

@router.delete("/api/visits/{visit_id}")
def delete_visit(visit_id: int, session: Session = Depends(get_session)):
    existing = session.get(Visit, visit_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Visit not found")
    session.delete(existing)
    session.commit()
    return {"message": "Visit deleted"}
