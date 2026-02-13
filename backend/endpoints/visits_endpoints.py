from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from miniorm.session import Session
from models import Visit, Pet, Vet, Procedure
from deps import get_session

router = APIRouter()

class VisitCreate(BaseModel):
    pet_id: int
    vet_id: int
    date: str
    procedure_id: int | None = None
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
    order_by: str = Query(None),
    order_dir: str = Query("ASC"),
):
    q = session.query(Visit)
    if order_by and order_by in ("visit_id", "pet_id", "vet_id", "date", "reason", "paid"):
        col = "pet" if order_by == "pet_id" else ("vet" if order_by == "vet_id" else order_by)
        q = q.order_by(col, order_dir or "ASC")
    if owner_id is not None:
        pets = session.query(Pet).filter(owner=owner_id).all()
        pet_ids = [p.pet_id for p in pets]
        all_visits = q.all()
        visits = [v for v in all_visits if v.pet and v.pet.pet_id in pet_ids]
    else:
        visits = q.all()
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
            "paid": v.paid,
            "procedure_ids": [p.procedure_id for p in (getattr(v, "procedures", None) or [])]
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
    if visit.procedure_id:
        from models import Procedure
        proc = session.get(Procedure, visit.procedure_id)
        if proc:
            # Ważne: musisz zainicjalizować listę, jeśli jest pusta
            if not hasattr(new_visit, 'procedures') or new_visit.procedures is None:
                new_visit.procedures = []
            
            new_visit.procedures.append(proc)
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

class AddProcedureBody(BaseModel):
    procedure_id: int

@router.post("/api/visits/{visit_id}/procedures")
def add_procedure_to_visit(visit_id: int, body: AddProcedureBody, session: Session = Depends(get_session)):
    procedure_id = body.procedure_id
    visit = session.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    proc = session.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    procs = getattr(visit, "procedures", None) or []
    if proc in procs:
        return {"message": "Procedure already on visit", "procedure_ids": [p.procedure_id for p in procs]}
    procs = list(procs) + [proc]
    setattr(visit, "procedures", procs)
    session.update(visit)
    session.commit()
    return {"message": "Procedure added", "procedure_ids": [p.procedure_id for p in procs]}

@router.delete("/api/visits/{visit_id}/procedures/{procedure_id}")
def remove_procedure_from_visit(visit_id: int, procedure_id: int, session: Session = Depends(get_session)):
    visit = session.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    procs = getattr(visit, "procedures", None) or []
    procs = [p for p in procs if p.procedure_id != procedure_id]
    setattr(visit, "procedures", procs)
    session.update(visit)
    session.commit()
    return {"message": "Procedure removed", "procedure_ids": [p.procedure_id for p in procs]}

@router.delete("/api/visits/{visit_id}")
def delete_visit(visit_id: int, session: Session = Depends(get_session)):
    existing = session.get(Visit, visit_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Visit not found")
    session.delete(existing)
    session.commit()
    return {"message": "Visit deleted"}
