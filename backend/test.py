import sys
import os
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

class Student(Person):
    student_id = Number(pk=True)
    age = Number()
    index = Number()
    class Meta:
        inheritance = "single"

class Teacher(Person):
    teacher_id = Number(pk=True)
    salary = Number()
    class Meta:
        inheritance = "single"

class Subject(MiniBase):
    id = Number(pk=True)
    name = Text()
    particpants = Relationship("Students", r_type="many-to-one", backref="subjects")
    teachers = Relationship("Teachers", r_type="many-to-one", backref="subjects")


db_path = "test.sqlite"
engine = DatabaseEngine(db_path=db_path)
generator = SchemaGenerator()
generator.create_all(engine, MiniBase._registry, drop_first=True) 
with Session(engine) as session:
    student1 = Student(first_name="Karolina", last_name="Nowak", age=22, index=12345) 
    student2 = Student(first_name="Maciej", last_name="Jakubowski", age=23, index=12346) 
    subject1 = Subject(name="Mathematics")
    subject2 = Subject(name="Physics")
    teacher1 = Teacher(first_name="Jan", last_name="Kowalski", salary=5000)
    teacher2 = Teacher(first_name="Anna", last_name="Sienkiewicz", salary=5000)
    
    subject1.teachers = [teacher2]
    subject2.teachers = [teacher1, teacher2]
    student1.subjects = [subject1, subject2]
    student2.subjects = [subject1]
    session.add(student1)
    session.add(student2)
    session.commit()

    student1.first_name = "Sylwia"
    session.commit()

    subjects = session.query(Subject).filter(Subject.name == "Mathematics").all()
    for subject in subjects:
        print(f"Subject: {subject.name}")
        print(f"Students:")
        particpants = subject.particpants
        students = particpants if isinstance(particpants, list) else ([particpants] if particpants else [])
        for student in students:
            print(f"  {student.first_name} {student.last_name}")
    print("--------------------------------")

    students = session.query(Student).join(Subject).join(Teacher).all()
    for student in students:
        print(f"Student: {student.first_name} {student.last_name}")
        print(f"Subjects:")
        for subject in student.subjects:
            print(f"  {subject.name}")
            for teacher in subject.teachers:
                print(f"    {teacher.first_name} {teacher.last_name}")
    print("--------------------------------")

    # students = session.query(Student).join(Subject).all()
    # for student in students:
    #     print(f"Student: {student.first_name} {student.last_name}")
    #     print(f"Subjects:")
    #     for subject in student.subjects:
    #         print(f"  {subject.name}")
    # print("--------------------------------")

    # students = session.query(Student).join(Subject).join(Teacher).filter((
    #     (Subject.name == "Physics")
    # )).all()
    # for student in students:
    #     print(f"Student: {student.first_name} {student.last_name}")
    #     print(f"Subjects:")
    #     for subject in student.subjects:
    #         print(f"  {subject.name} - Teachers:")
    #         for teacher in subject.teachers:
    #             print(f"    {teacher.first_name} {teacher.last_name}")
    # print("--------------------------------")

    # teachers = session.query(Teacher).join(Subject).join(Student).filter(
    #     Teacher.first_name == "Jan"
    # ).all()
    # for teacher in teachers:
    #     print(f"Teacher: {teacher.first_name} {teacher.last_name}")
    #     print(f"Subjects:")
    #     for subject in teacher.subjects:
    #         print(f"  {subject.name} - Students:")
    #         for student in subject.particpants:
    #             print(f"    {student.first_name} {student.last_name}")
    # print("--------------------------------")

    # session.delete(student1)
    # session.delete(subject1)
    # session.commit()

    # students = session.query(Student).all()
    # for student in students:
    #     print(f"Student: {student.first_name} {student.last_name}")
    #     print(f"Subjects:")
    #     for subject in student.subjects:
    #         print(f"  {subject.name}")
    # print("--------------------------------")

    # teachers = session.query(Teacher).all()
    # for teacher in teachers:
    #     print(f"Teacher: {teacher.first_name} {teacher.last_name}")
    #     print(f"Subjects:")
    #     for subject in teacher.subjects:
    #         print(f"  {subject.name}")