from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from miniorm import MiniBase
from miniorm.orm_types import Text, Number

from miniorm.database import DatabaseEngine
from miniorm.session import Session
from miniorm.generator import SchemaGenerator


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    text: str



from models import Person, Owner, Vet, Pet, Visit, Procedure

from endpoints.persons_endpoints import router as persons_router
from endpoints.owners_endpoints import router as owners_router
from endpoints.visits_endpoints import router as visits_router
from endpoints.pets_endpoints import router as pets_router
from endpoints.vets_endpoints import router as vets_router
from endpoints.procedures_endpoints import router as procedures_router

engine = DatabaseEngine("miniorm.sqlite")
SchemaGenerator().create_all(engine, MiniBase._registry, drop_first=False)

session = Session(engine)
app.state.session = session

app.include_router(persons_router)
app.include_router(owners_router)
app.include_router(visits_router)
app.include_router(pets_router)
app.include_router(vets_router)
app.include_router(procedures_router)

