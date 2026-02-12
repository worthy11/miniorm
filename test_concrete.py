from base import MiniBase
from orm_types import Number, Text, Relationship
from session import Session
from generator import SchemaGenerator
from database import DatabaseEngine
from test_utils import run_mapper_tests

class Person(MiniBase):
    id = Number(pk=True)
    name = Text()
    # age = Text()

    class Meta:
        table_name = "people"
        inheritance = "CONCRETE"

    def __repr__(self):
        return f"Person(id={self.id}, name={self.name})"

class Owner(Person):
    id = Number(pk=True)
    phone = Text()

    class Meta:
        table_name = "owners"
        inheritance = "CONCRETE"

    def __repr__(self):
        return f"Owner(id={self.id}, name={self.name}, phone={self.phone})"

class Vet(Person):
    id = Number(pk=True)
    specialization = Text()

    class Meta:
        table_name = "vets"
        inheritance = "CONCRETE"

    def __repr__(self):
        return f"Vet(id={self.id}, name={self.name}, specialization={self.specialization})"

class Pet(MiniBase):
    id = Number(pk=True)
    name = Text()
    owner = Relationship("owners", r_type="many-to-one")

    class Meta:
        table_name = "pets"

    def __repr__(self):
        return f"Pet(id={self.id}, name={self.name}, owner={self.owner})"

    def get_visits(self):
        return self.visits


class Visit(MiniBase):
    id = Number(pk=True)
    pet = Relationship("pets", r_type="many-to-one", backref="visits")
    procedures = Relationship("procedures", r_type="many-to-many", backref="visits")

    class Meta:
        table_name = "visits"

    def __repr__(self):
        return f"Visit(id={self.id}, pet={self.pet}, procedures={self.procedures})"

class Procedure(MiniBase):
    id = Number(pk=True)
    name = Text()
    visits = Relationship("visits", r_type="many-to-many", backref="procedures")

    class Meta:
        table_name = "procedures"

    def __repr__(self):
        return f"Procedure(id={self.id}, name={self.name}, visits={self.visits})"

if __name__ == "__main__":
    run_mapper_tests()
    engine = DatabaseEngine(db_path="db/test_concrete.db")

    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)
    
    with Session(engine) as session:
        owner = Owner(name="John Doeeee", phone="1234567890", age="33")
        session.add(owner)
        session.commit()

        vet = Vet(name="Jane Smithhhh", specialization="Cardiology")
        session.add(vet)
        session.commit()

        pet = Pet(name="Buddyyyy", owner=owner, species="dog")
        session.add(pet)
        session.commit()

        visit = Visit(pet=pet)
        session.add(visit)

        owners = session.query(Owner).all()
        for owner in owners:
            print(owner)

        vets = session.query(Vet).all()
        for vet in vets:
            print(vet)

        pets = session.query(Pet).all()
        for pet in pets:
            print(pet)
            print(pet.get_visits())

        visits = session.query(Visit).all()
        for visit in visits:
            print(visit)

        procedures = session.query(Procedure).all()
        for procedure in procedures:
            print(procedure)


        print("\n--- TEST MIGRACJI (ALTER TABLE) ---")
        pets = session.query(Pet).all()
        for p in pets:
            # Stare rekordy będą miały species=None
            # Nowy rekord (Rex) będzie miał species='Dog'
            print(f"Pet: {p.name}, Species: {getattr(p, 'species', 'N/A')}")
