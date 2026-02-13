from miniorm import MiniBase
from miniorm.orm_types import Text, Number, Relationship

class Person(MiniBase):
    class Meta:
        table_name = "persons"
        inheritance = "CONCRETE"
        discriminator = "person_type"
        discriminator_value = "person"
    person_id = Number(pk=True)
    first_name = Text()
    last_name = Text()
    email = Text()
    phone = Text()


class Owner(Person):
    class Meta:
        table_name = "owners"
        inheritance = "CONCRETE"
        discriminator_value = "owner"
    password = Text()

class Vet(Person):
    class Meta:
        table_name = "vets"
        inheritance = "CONCRETE"
        discriminator_value = "vet"
    license = Text()

class Pet(MiniBase):
    class Meta:
        table_name = "pets"
    pet_id = Number(pk=True)
    owner = Relationship("owners", backref="pets", r_type="many-to-one", cascade_delete=True)
    name = Text()
    species = Text()
    breed = Text()
    birth_date = Text()

class Visit(MiniBase):
    class Meta:
        table_name = "visits"
    visit_id = Number(pk=True)
    pet = Relationship("pets", backref="visits", r_type="many-to-one", cascade_delete=True)
    vet = Relationship("owners", backref="visits", r_type="many-to-one", cascade_delete=True)
    procedures = Relationship("procedures", backref="visits", r_type="many-to-many")
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