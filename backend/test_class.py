from miniorm.base import MiniBase
from miniorm.orm_types import Text, Number, Relationship
from miniorm.session import Session
from miniorm.database import DatabaseEngine
from miniorm.generator import SchemaGenerator
from miniorm.filters import col, and_, or_

class Person(MiniBase):
    id = Number(pk=True)
    name = Text()
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
        return f"<Student(id={self.person_id}, name={self.name}, last_name={self.last_name}, age={self.age}, index={self.index})>"

class GraduateStudent(Student):
    class Meta:
        inheritance = "CLASS"
        table_name = "graduate_students"
    graduation_date = Text()
    student_id = Relationship(pk=True, target="students", r_type="one-to-one", cascade_delete=True)

    def __repr__(self):
        return f"<GraduateStudent(id={self.student_id}, first_name={self.first_name}, last_name={self.last_name}, age={self.age}, index={self.index}, graduation_date={self.graduation_date})>"


class MasterStudent(Student):
    class Meta:
        inheritance = "CLASS"
        table_name = "master_students"
    master_thesis = Text()
    student_id = Relationship(pk=True, target="students", r_type="one-to-one", cascade_delete=True)

    def __repr__(self):
        return f"<MasterStudent(id={self.student_id}, first_name={self.first_name}, last_name={self.last_name}, age={self.age}, index={self.index}, master_thesis={self.master_thesis})>"


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
    people = session.query(Person).order_by(Person.last_name).all()
    for person in people:
        print(person)

    students = session.query(Student).order_by(Student.last_name).all()
    for student in students:
        print(student)
        print(student.subjects)

    employees = session.query(Employee).order_by(Employee.salary, "DESC").all()
    for employee in employees:
        print(employee)

    subjects = session.query(Subject).order_by(Subject.name).all()
    for subject in subjects:
        print(subject)

def test_insert():
    person = Person(first_name="Krzysztof", last_name="Kowalski")
    subjects = [Subject(name="Computer Science"), Subject(name="Mathematics")]
    student = Student(first_name="John", last_name="Doe", age=20, index="123456", subjects=subjects)
    employee = Employee(first_name="Jane", last_name="Smith", salary=50000, position="Manager")

    session.add(person)
    session.commit()

    session.add(student)
    session.commit()

    session.add(employee)
    session.commit()

    # print(f"DEBUG: Inserting subject...")
    # session.add(subject)
    # session.commit()

def test_update():
    # print(f"DEBUG: Updating people...")
    # people = session.query(Person).all()
    # for person in people:
    #     person.last_name = "Majewski"
    #     session.update(person)
    # session.commit()

    students = session.query(Student).all()
    subjects = session.query(Subject).all()
    for student in students:
        student.first_name = "Max"
        student.subjects = [subjects[0]]
        session.update(student)
    session.commit()

def test_delete():
    math = session.query(Subject).filter(col("name") == "Mathematics").first()
    session.delete(math)
    session.commit()

def test_inheritance():
    graduate_student = GraduateStudent(first_name="John", last_name="Doe", age=20, index="123456", graduation_date="2026-01-01")
    master_student = MasterStudent(first_name="Jane", last_name="Smith", age=22, index="123457", master_thesis="Master Thesis")
    subjects = [Subject(name="Computer Science"), Subject(name="Mathematics")]
    graduate_student.subjects = subjects
    master_student.subjects = subjects
    session.add(graduate_student)
    session.add(master_student)
    session.commit()

    graduate_student = session.query(GraduateStudent).all()
    for graduate in graduate_student:
        print(graduate)
        print(graduate.__dict__)
        print(graduate.subjects)

    master_student = session.query(MasterStudent).all()
    subjects = session.query(Subject).all()
    for master in master_student:
        master.subjects = [subjects[0]]
        session.update(master)
    session.commit()
    master_student = session.query(MasterStudent).all()
    for master in master_student:
        print(master)
        print(master.subjects)

    session.delete(graduate_student[0])
    session.delete(subjects[0])
    session.commit()

    graduate_student = session.query(GraduateStudent).all()
    for graduate in graduate_student:
        print(graduate)
        print(graduate.subjects)

    master_student = session.query(MasterStudent).all()
    for master in master_student:
        print(master)
        print(master.subjects)


def test_filters():
    student1 = Student(name="John", last_name="Doe", age=20, index="123456", subjects=[Subject(name="Mathematics")])
    student2 = Student(name="Jane", last_name="Smith", age=22, index="123457", subjects=[Subject(name="Computer Science")])
    session.add(student1)
    session.add(student2)
    session.commit()

    students = session.query(Student).join("subjects").filter(col("name").in_(["Mathematics"])).all()
    for student in students:
        print(student)

engine = DatabaseEngine(db_path="test_class.sqlite")
generator = SchemaGenerator()
generator.create_all(engine, MiniBase._registry, drop_first=True)

with Session(engine) as session:
    # test_insert()
    # test_update()
    # test_select()
    # test_delete()
    test_filters()