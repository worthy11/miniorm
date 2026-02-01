from base import MiniBase
from database import DatabaseEngine
from builder import QueryBuilder
from session import Session
from example import Department, Employee, Project, Number, resolve_all_relationships, Person, StudentSingle
from generator import SchemaGenerator
import logging

def test_complex_scenarios():
    resolve_all_relationships()
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)

    with Session(engine, builder) as session:
        print("\n--- 1. Test Kolejności INSERT (Rodzic + Dziecko) ---")
        dept = Department(name="IT")
        emp = Employee(name="Adam")
        
        emp.department = dept
        session.add(emp)
        
        session.commit()
        print(f"Zapisano: {dept.name} (ID:{dept.id}) i {emp.name} (DeptID:{emp.department_id})")

        print("\n--- 2. Test Widoczności DELETED w Query ---")
        session.delete(emp)
        
        employees = session.query(Employee).all()
        print(f"Liczba znalezionych pracowników (powinno być 0): {len(employees)}")
        session.rollback()

        print("\n--- 3. Test Kolejności DELETE (Dziecko przed Rodzicem) ---")
        session.delete(dept)
        try:
            session.commit()
            print("Pomyślnie usunięto całą strukturę w poprawnej kolejności.")
        except Exception as e:
            print(f"Błąd usuwania: {e}")

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


    if detached_emp:
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


def test_security_and_m2m_optimized():
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)
    
    print("\n--- 11. Test Penetracyjny: SQL Injection w nazwie tabeli ---")
    class HackedModel(MiniBase):
        __tablename__ = "users; DROP TABLE employees; --"
        id = Number(pk=True)

    try:
        mapper = MiniBase._registry[HackedModel]
        sql, _ = builder.build_select(mapper, {})
        print(f"BŁĄD: System wygenerował zapytanie! {sql}")
    except ValueError as e:
        print(f"SUKCES: System zablokował niebezpieczną nazwę: {e}")
    finally:
        if HackedModel in MiniBase._registry:
            del MiniBase._registry[HackedModel]

    print("\n--- 12. Test: Many-To-Many (Insert & Update & Delete) ---")
    with Session(engine, builder) as session:
        p1 = Project(name="CyberSecurity")
        p2 = Project(name="AI Development")
        e1 = Employee(name="Hacker")
        
        # 1. Insert z relacją
        e1.projects = [p1]
        session.add(e1)
        session.commit()
        print("Zapisano pracownika z 1 projektem.")

        # 2. Update (Dodanie drugiego projektu) - Delta Update
        e1.projects.append(p2)
        session.commit()
        print("Zaktualizowano: dodano drugi projekt.")

        # 3. Update (Usunięcie pierwszego projektu) - Delta Update
        e1.projects.remove(p1)
        session.commit()
        print("Zaktualizowano: usunięto pierwszy projekt.")
        
        # Weryfikacja
        check_e1 = session.query(Employee).filter(name="Hacker").first()
        print(f"Aktualne projekty w bazie: {[p.name for p in check_e1.projects]}")

def test_lazy_loading_full():
    # Czyścimy śmieci po poprzednich testach
    to_remove = [cls for cls in MiniBase._registry if "DROP TABLE" in getattr(cls, "__tablename__", "")]
    for cls in to_remove:
        del MiniBase._registry[cls]
        
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    
    print("\n--- 10. Test: Many-To-Many i Lazy Loading ---")
    generator.create_all(engine, MiniBase._registry)

    with Session(engine, builder) as session:
        it_dept = Department(name="IT Cloud")
        p1 = Project(name="System Migracji")
        p2 = Project(name="Bezpieczeństwo")
        
        emp1 = Employee(name="Kamil")
        emp2 = Employee(name="Marta")

        emp1.department = it_dept
        emp2.department = it_dept
        emp1.projects = [p1, p2] 
        emp2.projects = [p1]

        session.add(emp1)
        session.add(emp2)
        session.commit()
        print("Zapisano dane i zamknięto sesję (obiekty przeszły w EXPIRED).")

    # Nowa sesja - sprawdzamy dociąganie
    with Session(engine, builder) as session:
        print("\n--- Sprawdzanie Lazy Loadingu (Nowa Sesja) ---")
        kamil = session.query(Employee).filter(name="Kamil").first()
        
        # PRZYPADEK 1: Many-To-One
        dept_name = kamil.department.name 
        print(f"1. Many-to-One OK: {dept_name}")

        # PRZYPADEK 2: Many-To-Many
        projects = [p.name for p in kamil.projects]
        print(f"2. Many-to-Many OK: {projects}")
        
        # PRZYPADEK 3: One-To-Many
        dept = kamil.department
        colleagues = [e.name for e in dept.employees]
        print(f"3. One-to-Many OK: {colleagues}")

def test_unit_of_work_snapshots():
    print("\n--- 13. Test: Snapshoty i Auto-Refresh (EXPIRED) ---")
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)

    with Session(engine, builder) as session:
        d1 = Department(name="R&D")
        session.add(d1)
        session.commit() # Obiekt d1 staje się EXPIRED

        print(f"Stan obiektu po commit: {d1._orm_state}")
        
        print(f"Dociąganie nazwy (Lazy Refresh): {d1.name}")
        print(f"Stan po refreshu: {d1._orm_state}")

        # Test Dirty Checkingu
        d1.name = "R&D"
        print("Wykonuję flush (nie powinno być SQL UPDATE, bo nazwa ta sama)...")
        session.flush()

        d1.name = "Research and Development"
        print("Wykonuję flush (powinien być SQL UPDATE)...")
        session.flush()

def test_builder_universality():
    print("\n--- 16. Test: Uniwersalny Builder ---")
    engine = DatabaseEngine()
    builder = QueryBuilder()
    
    class MockMapper:
        table_name = "test_table"
        pk = "id"
    
    data = {"name": "Test", "value": 123, "type": "MockType"}
    sql, params = builder.build_insert(MockMapper(), data)
    
    print(f"Wygenerowany SQL: {sql}")
    if "type" in sql and "?" in sql:
        print("SUKCES: Builder poprawnie generuje zapytania ze słowników.")
    else:
        print("BŁĄD: SQL Buildera jest niepoprawny.")

if __name__ == "__main__":
    test_complex_scenarios()
    test_security_and_m2m_optimized()
    test_lazy_loading_full()
    test_unit_of_work_snapshots()
    test_builder_universality()
