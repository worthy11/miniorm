from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from miniorm.session import Session
from models import Owner, Person, Pet
from deps import get_session

router = APIRouter()

class OwnerRegister(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    password: str
    license: str = None

@router.post("/api/owners")
def register_owner(owner: OwnerRegister, session: Session = Depends(get_session)):
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

def _apply_owner_filters(owners, first_name, last_name, email, phone):
    if first_name:
        owners = [o for o in owners if o.first_name and first_name.lower() in o.first_name.lower()]
    if last_name:
        owners = [o for o in owners if o.last_name and last_name.lower() in o.last_name.lower()]
    if email:
        owners = [o for o in owners if o.email and email.lower() in o.email.lower()]
    if phone:
        owners = [o for o in owners if o.phone and phone.lower() in (o.phone or "").lower()]
    return owners

@router.get("/api/owners")
def get_owners(
    session: Session = Depends(get_session),
    first_name: str = Query(None),
    last_name: str = Query(None),
    email: str = Query(None),
    phone: str = Query(None),
    order_by: str = Query(None),
    order_dir: str = Query("ASC"),
):
    owners = session.query(Owner).all()
    owners = _apply_owner_filters(owners, first_name, last_name, email, phone)
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

class OwnerUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    password: str | None = None

@router.put("/api/owners/{owner_id}")
def update_owner(owner_id: int, owner: OwnerUpdate, session: Session = Depends(get_session)):
    existing = session.get(Owner, owner_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Owner not found")
    if owner.first_name is not None:
        setattr(existing, "first_name", owner.first_name)
    if owner.last_name is not None:
        setattr(existing, "last_name", owner.last_name)
    if owner.email is not None:
        setattr(existing, "email", owner.email)
    if owner.phone is not None:
        setattr(existing, "phone", owner.phone)
    if owner.password is not None:
        setattr(existing, "password", owner.password)
    session.update(existing)
    session.commit()
    return {
        "owner_id": existing.person_id,
        "first_name": existing.first_name,
        "last_name": existing.last_name,
        "email": existing.email,
        "phone": existing.phone,
        "message": "Owner updated"
    }

@router.delete("/api/owners/{owner_id}")
def delete_owner(owner_id: int, session: Session = Depends(get_session)):
    existing = session.get(Owner, owner_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Owner not found")
    session.delete(existing)
    session.commit()
    return {"message": "Owner deleted"}
