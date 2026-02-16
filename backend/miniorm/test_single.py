import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from miniorm.base import MiniBase
from miniorm.orm_types import Text, Number, Relationship
from miniorm.session import Session
from miniorm.database import DatabaseEngine
from miniorm.generator import SchemaGenerator

def test_single():
    class Worker(MiniBase):
        id = Number(pk=True)
        name = Text(unique=True)
        age = Number()
        class Meta:
            table_name = "workers"
            inheritance = "single"

    class Boss(Worker):
        departament = Text()
        class Meta:
            inheritance = "single"


    class Employee(Worker):
        salary = Number()
        manager_id = Relationship("Boss", r_type="many-to-one")
        class Meta:
            inheritance = "single"

    class Task(MiniBase):
        id = Number(pk=True)
        title = Text()
        description = Text()
        participants = Relationship("Worker", r_type="many-to-many", backref="tasks")
        class Meta:
            table_name = "tasks"

    class Departament(MiniBase):
        id = Number(pk=True)
        name = Text()
        boss = Relationship("Boss", r_type="one-to-one", cascade_delete=True)
        class Meta:
            table_name = "departaments"
    
    db_path = "test_single_rel.sqlite"
    if os.path.exists(db_path): os.remove(db_path)
    engine = DatabaseEngine(db_path=db_path)
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)   
    with Session(engine) as session:
        boss = Boss(name="Dyrektor Nowak", age=50, departament="IT")
        boss2 = Boss(name="Dyrektor Nowakowski", age=50, departament="IT")
        emp = Employee(name="Pracownik Kowalski", age=30, salary=5000)

        session.add(boss)
        session.add(emp)
        session.add(boss2)
        session.commit()

        
        task1 = Task(title="Task 1", description="Opis zadania 1")
        task2 = Task(title="Task 2", description="Opis zadania 2")
        task3 = Task(title="Task 3", description="Opis zadania 3")
        dpm = Departament(name="IT")
        session.add(dpm)

        session.add(task1)
        session.add(task2)
        session.add(task3)
        task2.participants.append(boss)
        dpm.boss = boss
        boss2.subordinates = emp
        boss.subordinates = emp

        emp.manager_id = boss
        
        session.commit()

        emp.manager_id = boss2
        session.commit()

        # session.delete(boss)


        # session.delete(boss2)
        # session.delete(boss2)
        # session.commit()

        # task3.title = "Julek"
        # task2.participants.remove(boss)
        session.commit()
       

if __name__ == "__main__":
    test_single()