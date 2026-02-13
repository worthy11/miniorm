from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from miniorm.session import Session
from models import Vet, Person
from deps import get_session

router = APIRouter()

class VetCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    license: str

def _apply_vet_filters(vets, first_name, last_name, email, phone, license_):
    if first_name:
        vets = [v for v in vets if v.first_name and first_name.lower() in v.first_name.lower()]
    if last_name:
        vets = [v for v in vets if v.last_name and last_name.lower() in v.last_name.lower()]
    if email:
        vets = [v for v in vets if v.email and email.lower() in v.email.lower()]
    if phone:
        vets = [v for v in vets if v.phone and phone.lower() in (v.phone or "").lower()]
    if license_:
        vets = [v for v in vets if v.license and license_.lower() in (v.license or "").lower()]
    return vets

@router.get("/api/vets")
def get_vets(
    session: Session = Depends(get_session),
    first_name: str = Query(None),
    last_name: str = Query(None),
    email: str = Query(None),
    phone: str = Query(None),
    license: str = Query(None, alias="license"),
    order_by: str = Query(None),
    order_dir: str = Query("ASC"),
):
    q = session.query(Vet)
    if order_by and order_by in ("vet_id", "first_name", "last_name", "email", "phone", "license"):
        col = "person_id" if order_by == "vet_id" else order_by
        q = q.order_by(col, order_dir or "ASC")
    vets = q.all()
    vets = _apply_vet_filters(vets, first_name, last_name, email, phone, license)
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
def add_vet(vet: VetCreate, session: Session = Depends(get_session)):
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

class VetUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    license: str | None = None

@router.put("/api/vets/{vet_id}")
def update_vet(vet_id: int, vet: VetUpdate, session: Session = Depends(get_session)):
    existing = session.get(Vet, vet_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Vet not found")
    if vet.first_name is not None:
        setattr(existing, "first_name", vet.first_name)
    if vet.last_name is not None:
        setattr(existing, "last_name", vet.last_name)
    if vet.email is not None:
        setattr(existing, "email", vet.email)
    if vet.phone is not None:
        setattr(existing, "phone", vet.phone)
    if vet.license is not None:
        setattr(existing, "license", vet.license)
    session.update(existing)
    session.commit()
    return {
        "vet_id": existing.person_id,
        "first_name": existing.first_name,
        "last_name": existing.last_name,
        "email": existing.email,
        "phone": existing.phone,
        "license": existing.license,
        "message": "Vet updated"
    }

@router.delete("/api/vets/{vet_id}")
def delete_vet(vet_id: int, session: Session = Depends(get_session)):
    existing = session.get(Vet, vet_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Vet not found")
    session.delete(existing)
    session.commit()
    return {"message": "Vet deleted"}
