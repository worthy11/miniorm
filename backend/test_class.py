from miniorm.base import MiniBase
from miniorm.orm_types import Text, Number, Relationship
from miniorm.session import Session
from miniorm.database import DatabaseEngine
from miniorm.generator import SchemaGenerator
from miniorm.filters import col, and_, or_

class Person(MiniBase):
    id = Number(pk=True)
    first_name = Text()
    last_name = Text()

    class Meta:
        inheritance = "CLASS"
        table_name = "persons"

    def __repr__(self):
        return f"<Person(id={self.id}, first_name={self.first_name}, last_name={self.last_name})>"

class Student(Person):
    class Meta:
        inheritance = "CLASS"
        table_name = "students"
    age = Number()
    index = Text()
    person_id = Relationship(pk=True, target="persons", r_type="one-to-one", cascade_delete=True)
    subjects = Relationship("subjects", r_type="many-to-many", cascade_delete=True)
    
    def __repr__(self):
        return f"<Student(id={self.person_id}, first_name={self.first_name}, last_name={self.last_name}, age={self.age}, index={self.index})>"


class Employee(Person):
    class Meta:
        inheritance = "CLASS"
        table_name = "employees"
    person_id = Relationship(pk=True, target="persons", r_type="one-to-one", cascade_delete=True)
    salary = Number()
    position = Text()

    def __repr__(self):
        return f"<Employee(id={self.person_id}, first_name={self.first_name}, last_name={self.last_name}, salary={self.salary}, position={self.position})>"

class Subject(MiniBase):
    subject_id = Number(pk=True)
    name = Text()
    # student = Relationship("students", backref="subjects", r_type="many-to-one", cascade_delete=True)

    class Meta:
        table_name = "subjects"

    def __repr__(self):
        return f"<Subject(id={self.subject_id}, name={self.name})>"


def test_select():
    print(f"DEBUG: Selecting people...")
    people = session.query(Person).order_by(Person.last_name).all()
    for person in people:
        print(person)

    print(f"DEBUG: Selecting students...")
    students = session.query(Student).order_by(Student.last_name).all()
    for student in students:
        print(student)
        print(student.subjects)

    print(f"DEBUG: Selecting employees...")
    employees = session.query(Employee).order_by(Employee.salary, "DESC").all()
    for employee in employees:
        print(employee)

    print(f"DEBUG: Selecting subjects...")
    subjects = session.query(Subject).order_by(Subject.name).all()
    for subject in subjects:
        print(subject)

def test_insert():
    person = Person(first_name="Krzysztof", last_name="Kowalski")
    subjects = [Subject(name="Computer Science"), Subject(name="Mathematics")]
    student = Student(first_name="John", last_name="Doe", age=20, index="123456", subjects=subjects)
    employee = Employee(first_name="Jane", last_name="Smith", salary=50000, position="Manager")

    print(f"DEBUG: Inserting people...")
    session.add(person)
    session.commit()

    print(f"DEBUG: Inserting student...")
    session.add(student)
    session.commit()

    print(f"DEBUG: Inserting employee...")
    session.add(employee)
    session.commit()

    # print(f"DEBUG: Inserting subject...")
    # session.add(subject)
    # session.commit()

def test_update():
    print(f"DEBUG: Updating people...")
    people = session.query(Person).all()
    for person in people:
        person.last_name = "Majewski"
        session.update(person)
    session.commit()

    print(f"DEBUG: Updating students...")
    students = session.query(Student).all()
    subjects = session.query(Subject).all()
    for student in students:
        student.first_name = "Max"
        student.subjects = [subjects[0]]
        session.update(student)
    session.commit()

def test_delete():
    # for person in session.query(Person).all():
    #     session.delete(person)

    for student in session.query(Student).all():
        print(f"DEBUG: Deleting student: {student}")
        session.delete(student)
    session.commit()


engine = DatabaseEngine(db_path="test_class.sqlite")
generator = SchemaGenerator()
generator.create_all(engine, MiniBase._registry, drop_first=True)

with Session(engine) as session:
    test_insert()
    test_update()
    test_select()
    print("--------------------------------")
    # test_select()
    # test_delete()