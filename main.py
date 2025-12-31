# from base import MiniBase
# from database import DatabaseEngine
# from builder import QueryBuilder
# from generator import SchemaGenerator
# from session import Session
# from example import Person, StudentSingle, resolve_all_relationships

# resolve_all_relationships()

# engine = DatabaseEngine()
# builder = QueryBuilder()
# generator = SchemaGenerator()
# session = Session(engine, builder)

# seen_tables = set()
# for cls in sorted(MiniBase._registry.keys(), key=lambda x: len(x.__mro__), reverse=True):
#     mapper = MiniBase._registry[cls]
#     if mapper.table_name not in seen_tables:
#         sql = generator.generate_create_table(mapper)
#         engine.execute(sql)
#         seen_tables.add(mapper.table_name)

# student = StudentSingle()
# student.name = "Kij Kijowski"
# student.grade = 5

# session.add(student)
# session.commit()

# queried_student = session.query(StudentSingle).filter(name="Kij Kijowski").first()
# print(f"Pobrany student: {queried_student.name}, ID: {queried_student.id}")
# print(f"To samo miejsce w RAM? {student is queried_student}")

# student2 = session.query(StudentSingle).filter(name="Nieistniejący").first()


# student.name = "jabuszko"
# print(student.name)
# session.flush()
# session.rollback()
# print(student.name)

from base import MiniBase
from database import DatabaseEngine
from builder import QueryBuilder
from session import Session
from example import Department, Employee, Project, resolve_all_relationships
from generator import SchemaGenerator
import logging

def test_complex_scenarios():
    resolve_all_relationships()
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    
    for model in [Department, Employee, Project]:
        mapper = MiniBase._registry[model]
        sql = generator.generate_create_table(mapper)
        engine.execute(sql)

    with Session(engine, builder) as session:
        print("\n--- 1. Test Kolejności INSERT (Rodzic + Dziecko) ---")
        dept = Department(name="IT")
        emp = Employee(name="Adam", department_id=None)
        
        session.add(emp)
        session.add(dept)
        
        session.flush()
        emp.department_id = dept.id
        session.commit()
        print(f"Zapisano: {dept.name} (ID:{dept.id}) i {emp.name} (DeptID:{emp.department_id})")

        print("\n--- 2. Test Widoczności DELETED w Query ---")
        session.delete(emp)
        
        employees = session.query(Employee).all()
        print(f"Liczba znalezionych pracowników (powinno być 0): {len(employees)}")
        session.rollback()

        # print("\n--- 3. Test Kolejności DELETE (Dziecko przed Rodzicem) ---")
        # session.delete(dept)
        # try:
        #     session.commit()
        #     print("Pomyślnie usunięto całą strukturę w poprawnej kolejności.")
        # except Exception as e:
        #     print(f"Błąd usuwania: {e}")

    with Session(engine, builder) as session:
        print("\n--- 4. Test Automatycznego Dirty Checking ---")
        dept_it = Department(name="HR")
        session.add(dept_it)
        session.commit()
        
        dept_it.name = "Human Resources" 
        session.commit()
        
        check_dept = engine.execute("SELECT name FROM departments WHERE id = ?", (dept_it.id,))
        print(f"Nazwa w bazie po automatycznym update: {check_dept[0]['name']}")

        print("\n--- 5. Test Identity Map i Rollback Delete ---")
        emp_test = Employee(name="Patryk")
        session.add(emp_test)
        session.commit()
        
        session.delete(emp_test)
        print(f"Stan przed rollback: {emp_test._orm_state}")
        
        session.rollback()
        print(f"Stan po rollback: {emp_test._orm_state}")
        print(f"Imię po wskrzeszeniu: {emp_test.name}")

        print("\n--- 6. Test Stanu DETACHED ---")
        detached_emp = session.query(Employee).filter(name="Patryk").first()


    print(f"Stan obiektu po zamknięciu sesji: {detached_emp._orm_state}")
    try:
        print(f"Dane odłączonego obiektu: {detached_emp.name}")
    except Exception as e:
        print(f"Błąd dostępu do danych: {e}")


    with Session(engine, builder) as session:
        print("\n--- 8. Test: Double Add (Add -> Delete -> Add) ---")
        new_dept = Department(name="Temporary")
        session.add(new_dept)
        session.flush()
        
        session.delete(new_dept)
        session.add(new_dept) 
        
        session.commit()
        res = session.query(Department).filter(name="Temporary").first()
        print(f"Czy departament przetrwał karuzelę stanów? {'Tak' if res else 'Nie'}")

    with Session(engine, builder) as session:
        print("\n--- 9. Test: Tożsamość referencji (is) ---")
        e1 = session.get(Employee, 2)
        e2 = session.get(Employee, 2)
        
        print(f"Czy e1 to ten sam obiekt co e2? {e1 is e2}")
        if e1 is e2:
            e1.name = "Nowe Imie Patryka"
            print(f"Zmiana w e1 widoczna w e2? {e2.name == 'Nowe Imie Patryka'}")


if __name__ == "__main__":
    test_complex_scenarios()