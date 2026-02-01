from fastapi import APIRouter
from pydantic import BaseModel
from miniorm.database import DatabaseEngine
from miniorm.builder import QueryBuilder
from miniorm.session import Session
from models import Person

router = APIRouter()

class PersonCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str

@router.post("/api/persons")
def create_person(person: PersonCreate):
    engine = DatabaseEngine("miniorm.sqlite")
    builder = QueryBuilder()
    new_person = Person(
        first_name=person.first_name,
        last_name=person.last_name,
        email=person.email,
        phone=person.phone
    )
    with Session(engine, builder) as session:
        session.add(new_person)
        session.commit()
        return {
            "person_id": new_person.person_id,
            "first_name": new_person.first_name,
            "last_name": new_person.last_name,
            "email": new_person.email,
            "phone": new_person.phone,
            "message": "Person created successfully"
        }
