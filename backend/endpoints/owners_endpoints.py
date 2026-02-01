from fastapi import APIRouter, Query
from pydantic import BaseModel
from miniorm.database import DatabaseEngine
from miniorm.builder import QueryBuilder
from miniorm.session import Session
from models import Owner, Person, Pet

router = APIRouter()

class OwnerRegister(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    password: str
    license: str = None

@router.post("/api/owners")
def register_owner(owner: OwnerRegister):
    engine = DatabaseEngine("miniorm.sqlite")
    builder = QueryBuilder()
  
    with Session(engine, builder) as session:
        new_owner = Owner(
            first_name=owner.first_name,
            last_name=owner.last_name,
            email=owner.email,
            phone=owner.phone,
            password=owner.password
        )
        session.add(new_owner)
        session.commit()
        return {
            "owner_id": new_owner.person_id,
            "first_name": new_owner.first_name,
            "last_name": new_owner.last_name,
            "email": new_owner.email,
            "phone": new_owner.phone,
            "message": "Owner registered successfully"
        }

@router.get("/api/owners")
def get_owners(email: str = Query(None), password: str = Query(None)):
    engine = DatabaseEngine("miniorm.sqlite")
    builder = QueryBuilder()
    with Session(engine, builder) as session:
        
        if email and password:
            owners = [o for o in session.query(Owner).all() if o.email == email and o.password == password]
        elif email:
            owners = [o for o in session.query(Owner).all() if o.email == email]
        else:
            owners = session.query(Owner).all()
        return [
            {
                "owner_id": o.person_id,
                "first_name": o.first_name,
                "last_name": o.last_name,
                "email": o.email,
                "phone": o.phone
            }
            for o in owners
        ]
