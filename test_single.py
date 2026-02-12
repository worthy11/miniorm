from base import MiniBase
from orm_types import Number, Text, Relationship
from session import Session
from generator import SchemaGenerator
from database import DatabaseEngine
from test_utils import run_mapper_tests

class Person(MiniBase):
    id = Number(pk=True)
    name = Text()

    class Meta:
        table_name = "people"
        inheritance = "SINGLE"

    def __repr__(self):
        return f"Person(id={self.id}, name={self.name})"

class Owner(Person):
    phone = Text()

    class Meta:
        table_name = "owners"
        inheritance = "SINGLE"

    def __repr__(self):
        return f"Owner(id={self.id}, name={self.name}, phone={self.phone})"

class Vet(Person):
    specialization = Text()

    class Meta:
        table_name = "vets"
        inheritance = "SINGLE"

    def __repr__(self):
        return f"Vet(id={self.id}, name={self.name}, specialization={self.specialization})"

class StudentVet(Vet):
    grade = Number()

    class Meta:
        table_name = "student_vets"
        inheritance = "SINGLE"
        discriminator_value = "StudentVet"

class Pet(MiniBase):
    id = Number(pk=True)
    name = Text()
    owner = Relationship("people", r_type="many-to-one", cascade_delete=True)

    class Meta:
        table_name = "pets"

    def __repr__(self):
        return f"Pet(id={self.id}, name={self.name}, owner={self.owner})"


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
    engine = DatabaseEngine(db_path="db/test_single.db")

    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)
    
    with Session(engine) as session:
        owner = Owner(name="John Doe", phone="1234567890", birth_date="2004", bonus_points=10)
        session.add(owner)
        # session.commit()

        vet = Vet(name="Jane Smith", specialization="Cardiology", birth_date="2006", bonus_points=30)
        session.add(vet)
        # session.commit()

        pet = Pet(name="Buddy", owner=owner)
        session.add(pet)
        # session.commit()

        people = session.query(Person).all()
        for person in people:
            print(person)

        # owners = session.query(Owner).all()
        # for owner in owners:
        #     print(owner)
        #     session.delete(owner)

        vets = session.query(Vet).all()
        for vet in vets:
            print(vet)
            vet.name = "Bim bam bom"
            vet.specialization = "ABCDEFG"
            session.update(vet)

        pets = session.query(Pet).all()
        for pet in pets:
            print(pet)

        visits = session.query(Visit).all()
        for visit in visits:
            print(visit)

        procedures = session.query(Procedure).all()
        for procedure in procedures:
            print(procedure)

        new_student = StudentVet(name="John Doe", specialization="Cardiology", grade=10)
        session.add(new_student)
        