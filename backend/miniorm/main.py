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

from .base import MiniBase
from .database import DatabaseEngine
from .builder import QueryBuilder
from .session import Session
from .example import Department, Employee, Project, Number, resolve_all_relationships
from .generator import SchemaGenerator
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


    # # 1. Przygotowanie tabel (w tym asocjacyjnej)
    # print("\n--- 10. Test: Many-To-Many i Lazy Loading ---")
    # for model in [Department, Employee, Project]:
    #     mapper = MiniBase._registry[model]
    #     engine.execute(generator.generate_create_table(mapper))
    #     # Tworzymy tabele asocjacyjne dla M2M
    #     for rel in mapper.relationships.values():
    #         if rel.r_type == "many-to-many":
    #             # Prosty SQL dla tabeli łączącej, jeśli generator go nie wspiera
    #             sql = f"CREATE TABLE IF NOT EXISTS {rel.association_table} ({rel._resolved_local_key} INTEGER, {rel._resolved_remote_key} INTEGER)"
    #             engine.execute(sql)

    # with Session(engine, builder) as session:
    #     # 2. Tworzenie danych
    #     it_dept = Department(name="IT Cloud")
    #     p1 = Project(name="System Migracji")
    #     p2 = Project(name="Bezpieczeństwo")
        
    #     emp1 = Employee(name="Kamil")
    #     emp2 = Employee(name="Marta")

    #     # Przypisanie departamentu (Many-To-One)
    #     emp1.department = it_dept
    #     emp2.department = it_dept

    #     # Przypisanie projektów (Many-To-Many)
    #     # Zakładamy, że w Employee masz pole 'projects'
    #     emp1.projects = [p1, p2] 
    #     emp2.projects = [p1]

    #     session.add(emp1)
    #     session.add(emp2)
    #     session.commit()
    #     print("Zapisano pracowników, departament i projekty (M2M).")

    # # 3. Test Lazy Loadingu w nowej sesji
    # with Session(engine, builder) as session:
    #     print("\n--- Sprawdzanie Lazy Loadingu ---")
    #     kamil = session.query(Employee).filter(name="Kamil").first()
        
    #     # Test Many-To-One (Pracownik -> Departament)
    #     print(f"Pracownik: {kamil.name}")
    #     print(f"Dociąganie departamentu (Lazy): {kamil.department.name}")

    #     # Test Many-To-Many (Pracownik -> Projekty)
    #     # To wywoła Twoje __getattribute__ -> _load_m2m -> _query_m2m
    #     print(f"Dociąganie projektów (Lazy M2M): {[p.name for p in kamil.projects]}")
        
    #     # Test One-To-Many (Departament -> Pracownicy)
    #     dept = kamil.department
    #     print(f"Pracownicy departamentu {dept.name}: {[e.name for e in dept.employees]}")

def test_security_and_m2m_optimized():
        engine = DatabaseEngine()
        builder = QueryBuilder()
        generator = SchemaGenerator()
        generator.create_all(engine, MiniBase._registry)
        
        print("\n--- 11. Test Penetracyjny: SQL Injection w nazwie tabeli ---")
        # Udajemy, że haker próbuje przejąć kontrolę przez nazwę tabeli
        class HackedModel(MiniBase):
            __tablename__ = "users; DROP TABLE employees; --"
            id = Number(pk=True)

        try:
            # Próba wygenerowania zapytania dla złośliwego modelu
            mapper = MiniBase._registry[HackedModel]
            sql, _ = builder.build_select(mapper, {})
            print(f"BŁĄD: System wygenerował zapytanie! {sql}")
        except ValueError as e:
            print(f"SUKCES: System zablokował niebezpieczną nazwę: {e}")
        finally:
        # Musimy posprzątać w rejestrze, żeby inne testy nie wybuchały
            if HackedModel in MiniBase._registry:
                del MiniBase._registry[HackedModel]

        print("\n--- 12. Test: Many-To-Many bez duplikowania i rekurencji ---")
        # Tutaj testujemy Twoją nową, zoptymalizowaną metodę _flush_m2m
        with Session(engine, builder) as session:
            p1 = Project(name="CyberSecurity")
            e1 = Employee(name="Hacker")
            
            # Przypisujemy relację M2M
            e1.projects = [p1]
            session.add(e1)
            
            # Wywołujemy flush dwa razy - system nie może rzucić błędem ani zdublować wpisów
            session.flush()
            session.flush() 
            print("Sukces: Podwójny flush nie wywołał błędu UNIQUE constraint.")

            session.commit()    

    
def test_lazy_loading_full():
    to_remove = [cls for cls in MiniBase._registry if "DROP TABLE" in getattr(cls, "__tablename__", "")]
    for cls in to_remove:
        del MiniBase._registry[cls]
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    
    print("\n--- 10. Test: Many-To-Many i Lazy Loading ---")
    # Automatyczne tworzenie wszystkiego (w tym tabel M2M!)
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
        # Powinno wygenerować: SELECT * FROM departments WHERE id = ...
        dept_name = kamil.department.name 
        print(f"1. Many-to-One OK: {dept_name}")

        # PRZYPADEK 2: Many-To-Many
        # Powinno wygenerować: SELECT * FROM projects JOIN employee_project ...
        projects = [p.name for p in kamil.projects]
        print(f"2. Many-to-Many OK: {projects}")
        
        # PRZYPADEK 3: One-To-Many
        # Powinno wygenerować: SELECT * FROM employees WHERE department_id = ...
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
        
        # To wywoła __getattribute__ -> session.refresh()
        print(f"Dociąganie nazwy (Lazy Refresh): {d1.name}")
        print(f"Stan po refreshu: {d1._orm_state}")

        # Test Dirty Checkingu: zmieniamy na to samo
        d1.name = "R&D"
        # Jeśli snapshot działa, flush nie powinien wygenerować UPDATE
        print("Wykonuję flush (nie powinno być SQL UPDATE, bo nazwa ta sama)...")
        session.flush()

        # Zmieniamy faktycznie
        d1.name = "Research and Development"
        print("Wykonuję flush (powinien być SQL UPDATE)...")
        session.flush()

def test_polymorphic_loading():
    print("\n--- 14. Test: Polimorficzne ładowanie (STI) ---")
    from example import Person, StudentSingle
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)

    with Session(engine, builder) as session:
        s1 = StudentSingle(name="Student Jan", grade=5)
        session.add(s1)
        session.commit()

    with Session(engine, builder) as session:
        # Pobieramy przez klasę bazową Person
        person = session.query(Person).filter(name="Student Jan").first()
        print(f"Pobrano obiekt klasy: {type(person).__name__}")
        if isinstance(person, StudentSingle):
            print(f"Sukces: Polimorfizm działa, ocena: {person.grade}")
        else:
            print("Błąd: System nie rozpoznał klasy potomnej!")


def test_circular_dependency_error():
    print("\n--- 15. Test: Wykrywanie cykli w grafie ---")
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)

    with Session(engine, builder) as session:
        d1 = Department(name="Loop Dept")
        e1 = Employee(name="Loop Emp")
        
        # 1. Kierunek: Employee -> Department (FK w Employee)
        e1.department = d1
        
        # 2. Kierunek: Department -> Employee (FK w Department)
        # Aby graf to wykrył, musimy zasymulować relację Many-To-One w Departamencie
        from orm_types import Relationship
        circular_rel = Relationship(target=Employee, r_type="many-to-one")
        circular_rel._resolved_target = Employee
        circular_rel._resolved_fk_name = "manager_id"
        
        # Wstrzykujemy relację do mappera tylko dla tego testu
        Department._mapper.relationships["manager"] = circular_rel
        d1.manager = e1
        
        try:
            print("Próba zapisu cyklicznie zależnych obiektów...")
            session.add(e1)
            session.add(d1)
            session.flush() # To wywoła sortowanie i powinno rzucić RuntimeError
            print("BŁĄD: System nie wykrył cyklu i próbował wysłać SQL!")
        except RuntimeError as e:
            print(f"SUKCES: Graf wykrył cykl i zablokował zapis: {e}")
        finally:
            # Sprzątamy po "wstrzykniętej" relacji, by nie psuć innych testów
            if "manager" in Department._mapper.relationships:
                del Department._mapper.relationships["manager"]

def test_builder_universality():
    print("\n--- 16. Test: Uniwersalny Builder ---")
    engine = DatabaseEngine()
    builder = QueryBuilder()
    
    # Tworzymy mock mappera i dane
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
    # test_lazy_loading_full()
    test_unit_of_work_snapshots()
    # test_polymorphic_loading()
    test_circular_dependency_error()
    test_builder_universality()
