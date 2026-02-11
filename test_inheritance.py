from base import MiniBase
from orm_types import Text, Number, Relationship
from test_utils import run_mapper_tests


# SINGLE
class PersonSingle(MiniBase):
    id = Number(pk=True)
    name = Text()

    class Meta:
        table_name = "people"
        discriminator = "type"
        discriminator_value = "PersonSingle"


class StudentSingle(PersonSingle):
    grade = Number()

    class Meta:
        inheritance = "SINGLE"
        discriminator_value = "StudentSingle"


class TeacherSingle(PersonSingle):
    subject = Text()

    class Meta:
        inheritance = "SINGLE"
        discriminator_value = "TeacherSingle"


# CLASS
class PersonClass(MiniBase):
    id = Number(pk=True)
    name = Text()

    class Meta:
        table_name = "persons"
        inheritance = "CLASS"


class StudentClass(PersonClass):
    grade = Number()
    person_id = Relationship(PersonClass, r_type="one-to-one", pk=True)

    class Meta:
        inheritance = "CLASS"


class TeacherClass(PersonClass):
    subject = Text()
    person_id = Relationship(PersonClass, r_type="one-to-one", pk=True)

    class Meta:
        inheritance = "CLASS"


# CONCRETE
class PersonConcrete(MiniBase):
    id = Number(pk=True)
    name = Text()

    class Meta:
        table_name = "persons"


class StudentConcrete(PersonConcrete):
    grade = Number()

    class Meta:
        inheritance = "CONCRETE"


class TeacherConcrete(PersonConcrete):
    subject = Text()

    class Meta:
        inheritance = "CONCRETE"


class Standalone(MiniBase):
    id = Number(pk=True)
    title = Text()

    class Meta:
        table_name = "standalones"


if __name__ == "__main__":
    run_mapper_tests()
