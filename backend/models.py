
from miniorm import MiniBase
from miniorm.orm_types import Text, Number, Relationship


class Person(MiniBase):
    class Meta:
        table_name = "persons"
        discriminator = "person_type"
        discriminator_value = "person"
    person_id = Number(pk=True)
    first_name = Text()
    last_name = Text()
    email = Text()
    phone = Text()


class Pet(MiniBase):
    class Meta:
        table_name = "pets"
    pet_id = Number(pk=True)
    owner = Relationship("Owner", backref="pets", r_type="many-to-one")
    name = Text()
    species = Text()
    breed = Text()
    birth_date = Text()


class Owner(Person):
    class Meta:
        inheritance = "SINGLE"
        discriminator_value = "owner"
    password = Text()


class Vet(Person):
    class Meta:
        inheritance = "SINGLE"
        discriminator_value = "vet"
    license = Text()


class Visit(MiniBase):
    class Meta:
        table_name = "visits"
    visit_id = Number(pk=True)
    pet = Relationship(Pet, backref="visits", r_type="many-to-one")
    vet = Relationship(Vet, backref="visits", r_type="many-to-one")
    date = Text()
    reason = Text()
    paid = Number()


class Procedure(MiniBase):
    class Meta:
        table_name = "procedures"
    procedure_id = Number(pk=True)
    name = Text()
    description = Text()
    price = Number()


class VisitProcedure(MiniBase):
    class Meta:
        table_name = "visits_procedures"
    visit_procedure_id = Number(pk=True)
    visit = Relationship(Visit, backref="visit_procedures", r_type="many-to-one")
    procedure = Relationship(Procedure, backref="visit_procedures", r_type="many-to-one")
