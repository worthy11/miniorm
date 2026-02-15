from miniorm.base import MiniBase
from miniorm.orm_types import Text, Number, Relationship
from miniorm.session import Session
from miniorm.database import DatabaseEngine
from miniorm.generator import SchemaGenerator

class Person(MiniBase):
    person_id = Number(pk=True)
    first_name = Text()
    last_name = Text()

    class Meta:
        inheritance = "SINGLE"
        table_name = "persons"

    def __repr__(self):
        return f"<Person(id={self.person_id}, first_name={self.first_name}, last_name={self.last_name})>"

class Student(Person):
    class Meta:
        inheritance = "SINGLE"
        table_name = "students"
    age = Number()
    index = Text()
    subjects = Relationship("subjects", r_type="many-to-many", backref="students", cascade_delete=True)
    
    def __repr__(self):
        return f"<Student(id={self.person_id}, first_name={self.first_name}, last_name={self.last_name}, age={self.age}, index={self.index})>"


class Employee(Person):
    class Meta:
        inheritance = "SINGLE"
        table_name = "employees"
    salary = Number()
    position = Text()

    def __repr__(self):
        return f"<Employee(id={self.person_id}, first_name={self.first_name}, last_name={self.last_name}, salary={self.salary}, position={self.position})>"

class Subject(MiniBase):
    subject_id = Number(pk=True)
    name = Text()

    class Meta:
        table_name = "subjects"

    def __repr__(self):
        return f"<Subject(id={self.subject_id}, name={self.name})>"


def test_select():
    people = session.query(Person).order_by(Person.last_name).all()
    for person in people:
        print(person)

    students = session.query(Student).order_by(Student.last_name).all()
    for student in students:
        print(student)

    employees = session.query(Employee).order_by(Employee.salary, "DESC").all()
    for employee in employees:
        print(employee)

    subjects = session.query(Subject).order_by(Subject.name).all()
    for subject in subjects:
        print(subject)

def test_insert():
    person = Person(first_name="Krzysztof", last_name="Kowalski")
    subjects = [Subject(name="Math"), Subject(name="Science"), Subject(name="History")]
    student = Student(first_name="John", last_name="Doe", age=20, index="123456", subjects=subjects)
    employee = Employee(first_name="Jane", last_name="Smith", salary=50000, position="Manager")
    session.add(student)
    session.add(employee)
    session.add(person)
    session.commit()

def test_update():
    people = session.query(Person).all()
    for person in people:
        person.last_name = "Majewski"
        session.update(person)
    session.commit()

    students = session.query(Student).all()
    for student in students:
        student.first_name = "Max"
        session.update(student)

    session.commit()

def test_delete():
    employee = session.query(Employee).filter(first_name="Jane").first()
    session.delete(employee)
    session.commit()


engine = DatabaseEngine(db_path="test_single.sqlite")
generator = SchemaGenerator()
generator.create_all(engine, MiniBase._registry, drop_first=True)

with Session(engine) as session:
    test_insert()
    test_select()
    print("--------------------------------")
    test_update()
    test_select()
    test_delete()