from base import MiniBase
from orm_types import Number, Text, Relationship
from test_utils import print_mapper_info, run_mapper_tests

class Person(MiniBase):
    id = Number(pk=True)
    name = Text()

    class Meta:
        table_name = "people"

class Owner(Person):
    phone = Text()
    person_id = Relationship("people", r_type="one-to-one", pk=True)

    class Meta:
        table_name = "owners"
        inheritance = "CLASS"

class Vet(Person):
    specialization = Text()
    person_id = Relationship("people", r_type="one-to-one", pk=True)

    class Meta:
        table_name = "vets"
        inheritance = "CLASS"

class Pet(MiniBase):
    id = Number(pk=True)
    name = Text()
    owner = Relationship("owners", r_type="many-to-one")

    class Meta:
        table_name = "pets"


class Visit(MiniBase):
    id = Number(pk=True)
    pet = Relationship("pets", r_type="many-to-one", backref="visits")
    procedures = Relationship("procedures", r_type="many-to-many", backref="visits")

    class Meta:
        table_name = "visits"

class Procedure(MiniBase):
    id = Number(pk=True)
    name = Text()
    visits = Relationship("visits", r_type="many-to-many", backref="procedures")

    class Meta:
        table_name = "procedures"

if __name__ == "__main__":
    run_mapper_tests()
