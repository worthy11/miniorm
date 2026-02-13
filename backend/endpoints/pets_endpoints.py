from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from miniorm.session import Session
from models import Pet, Owner, Person
from deps import get_session

router = APIRouter()

class PetCreate(BaseModel):
    owner_id: int
    name: str
    species: str
    breed: str
    birth_date: str

def _apply_pet_filters(pets, owner_id, name, species, breed, birth_date):
    if owner_id is not None:
        pets = [p for p in pets if p.owner and p.owner.person_id == owner_id]
    if name:
        pets = [p for p in pets if p.name and name.lower() in p.name.lower()]
    if species:
        pets = [p for p in pets if p.species and species.lower() in p.species.lower()]
    if breed:
        pets = [p for p in pets if p.breed and breed.lower() in p.breed.lower()]
    if birth_date:
        pets = [p for p in pets if p.birth_date and birth_date in (p.birth_date or "")]
    return pets

@router.get("/api/pets")
def get_pets(
    session: Session = Depends(get_session),
    owner_id: int = Query(None),
    name: str = Query(None),
    species: str = Query(None),
    breed: str = Query(None),
    birth_date: str = Query(None),
    order_by: str = Query(None),
    order_dir: str = Query("ASC"),
):
    q = session.query(Pet)
    if order_by and order_by in ("pet_id", "owner_id", "name", "species", "breed", "birth_date"):
        col = "owner" if order_by == "owner_id" else order_by
        q = q.order_by(col, order_dir or "ASC")
    if owner_id is not None:
        owner = session.get(Owner, owner_id)
        if not owner:
            return []
        pets = q.filter(owner=owner_id).all()
    else:
        pets = q.all()
    pets = _apply_pet_filters(pets, owner_id, name, species, breed, birth_date)
    return [
        {
            "pet_id": p.pet_id,
            "owner": p.owner.person_id if p.owner else None,
            "name": p.name,
            "species": p.species,
            "breed": p.breed,
            "birth_date": p.birth_date
        }
        for p in pets
    ]

@router.post("/api/pets")
def add_pet(pet: PetCreate, session: Session = Depends(get_session)):
    owner = session.get(Owner, pet.owner_id)
    if not owner:
        return {"message": "Owner not found"}
    new_pet = Pet(
        owner=owner,
        name=pet.name,
        species=pet.species,
        breed=pet.breed,
        birth_date=pet.birth_date
    )
    session.add(new_pet)
    session.commit()
    return {
        "pet_id": new_pet.pet_id,
        "name": new_pet.name,
        "species": new_pet.species,
        "breed": new_pet.breed,
        "birth_date": new_pet.birth_date,
        "message": "Pet added successfully"
    }

class PetUpdate(BaseModel):
    owner_id: int | None = None
    name: str | None = None
    species: str | None = None
    breed: str | None = None
    birth_date: str | None = None

@router.put("/api/pets/{pet_id}")
def update_pet(pet_id: int, pet: PetUpdate, session: Session = Depends(get_session)):
    existing = session.get(Pet, pet_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Pet not found")
    if pet.owner_id is not None:
        owner = session.get(Owner, pet.owner_id)
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
        setattr(existing, "owner", owner)
    if pet.name is not None:
        setattr(existing, "name", pet.name)
    if pet.species is not None:
        setattr(existing, "species", pet.species)
    if pet.breed is not None:
        setattr(existing, "breed", pet.breed)
    if pet.birth_date is not None:
        setattr(existing, "birth_date", pet.birth_date)
    session.update(existing)
    session.commit()
    return {
        "pet_id": existing.pet_id,
        "name": existing.name,
        "species": existing.species,
        "breed": existing.breed,
        "birth_date": existing.birth_date,
        "message": "Pet updated"
    }

@router.delete("/api/pets/{pet_id}")
def delete_pet(pet_id: int, session: Session = Depends(get_session)):
    existing = session.get(Pet, pet_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Pet not found")
    session.delete(existing)
    session.commit()
    return {"message": "Pet deleted"}
