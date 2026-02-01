from fastapi import APIRouter
from pydantic import BaseModel
from miniorm.database import DatabaseEngine
from miniorm.builder import QueryBuilder
from miniorm.session import Session
from models import Vet, Person

router = APIRouter()

class VetCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    license: str

@router.get("/api/vets")
def get_vets():
    engine = DatabaseEngine("miniorm.sqlite")
    builder = QueryBuilder()
    with Session(engine, builder) as session:
        vets = session.query(Vet).all()
        return [
            {
                "vet_id": v.person_id,
                "first_name": v.first_name,
                "last_name": v.last_name,
                "email": v.email,
                "phone": v.phone,
                "license": v.license
            }
            for v in vets
        ]

@router.post("/api/vets")
def add_vet(vet: VetCreate):
    engine = DatabaseEngine("miniorm.sqlite")
    builder = QueryBuilder()
    with Session(engine, builder) as session:
        new_vet = Vet(
            first_name=vet.first_name,
            last_name=vet.last_name,
            email=vet.email,
            phone=vet.phone,
            license=vet.license
        )
        session.add(new_vet)
        session.commit()
        return {
            "vet_id": new_vet.person_id,
            "first_name": new_vet.first_name,
            "last_name": new_vet.last_name,
            "email": new_vet.email,
            "phone": new_vet.phone,
            "license": new_vet.license,
            "message": "Vet added successfully"
        }
