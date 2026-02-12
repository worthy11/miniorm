from fastapi import APIRouter, Depends
from pydantic import BaseModel
from miniorm.session import Session
from models import Person
from deps import get_session

router = APIRouter()

class PersonCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str

@router.post("/api/persons")
def create_person(person: PersonCreate, session: Session = Depends(get_session)):
    new_person = Person(
        first_name=person.first_name,
        last_name=person.last_name,
        email=person.email,
        phone=person.phone
    )
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
