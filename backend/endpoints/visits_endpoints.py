from fastapi import APIRouter, Query
from pydantic import BaseModel
from miniorm.database import DatabaseEngine
from miniorm.builder import QueryBuilder
from miniorm.session import Session
from models import Visit, Pet, Vet

router = APIRouter()

class VisitCreate(BaseModel):
    pet_id: int
    vet_id: int
    date: str
    reason: str
    paid: int


@router.get("/api/visits")
def get_visits(owner_id: int = None):
    engine = DatabaseEngine("miniorm.sqlite")
    builder = QueryBuilder()
    with Session(engine, builder) as session:
        if owner_id is not None:
            # Get all pets for this owner
            from models import Pet
            pets = session.query(Pet).filter(lambda p: p.owner.person_id == owner_id).all()
            pet_ids = [p.pet_id for p in pets]
            visits = session.query(Visit).filter(lambda v: v.pet.pet_id in pet_ids).all()
        else:
            visits = session.query(Visit).all()
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
def add_visit(visit: VisitCreate):
    engine = DatabaseEngine("miniorm.sqlite")
    builder = QueryBuilder()
    with Session(engine, builder) as session:
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
