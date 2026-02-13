from miniorm.base import MiniBase
from miniorm.orm_types import Text, Number, Relationship
from miniorm.session import Session
from miniorm.database import DatabaseEngine
from miniorm.generator import SchemaGenerator

class Person(MiniBase):
    first_name = Text()
    last_name = Text()

    class Meta:
        inheritance = "SINGLE"
        table_name = "persons"
        discriminator = "person_type"
        discriminator_value = "person"

class Student(Person):
    class Meta:
        inheritance = "SINGLE"
        table_name = "persons"
        discriminator = "person_type"
        discriminator_value = "student"
    age = Number()
    index = Text()

    subjects = Relationship("Subject", r_type="many-to-many", cascade_delete=True)


class Employee(Person):
    class Meta:
        inheritance = "SINGLE"
        table_name = "persons"
        discriminator = "person_type"
        discriminator_value = "employee"
    salary = Number()
    position = Text()

class Subject(MiniBase):
    name = Text()

engine = DatabaseEngine(db_path="test.sqlite")
generator = SchemaGenerator()
generator.create_all(engine, MiniBase._registry)
session = Session(engine)