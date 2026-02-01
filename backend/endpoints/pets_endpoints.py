from fastapi import APIRouter, Query
from pydantic import BaseModel
from miniorm.database import DatabaseEngine
from miniorm.builder import QueryBuilder
from miniorm.session import Session
from models import Pet, Owner, Person

router = APIRouter()

class PetCreate(BaseModel):
    owner_id: int
    name: str
    species: str
    breed: str
    birth_date: str

@router.get("/api/pets")
def get_pets(owner_id: int = Query(...)):
    engine = DatabaseEngine("miniorm.sqlite")
    builder = QueryBuilder()
    with Session(engine, builder) as session:
        owner = session.get(Owner, owner_id)
        if not owner:
            return []
        pets = session.query(Pet).all()
        pets_for_owner = [p for p in pets if getattr(p.owner, 'person_id', None) == owner_id]
        return [
            {
                "pet_id": p.pet_id,
                "name": p.name,
                "species": p.species,
                "breed": p.breed,
                "birth_date": p.birth_date
            }
            for p in pets_for_owner
        ]

@router.post("/api/pets")
def add_pet(pet: PetCreate):
    engine = DatabaseEngine("miniorm.sqlite")
    builder = QueryBuilder()
    with Session(engine, builder) as session:
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
