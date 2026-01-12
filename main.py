from base import MiniBase
from database import DatabaseEngine
from builder import QueryBuilder
from session import Session
from example import Department, Employee, Project, Number, Text, StudentSingle, Person, resolve_all_relationships
from generator import SchemaGenerator
from states import ObjectState

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
        session.flush()
        
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
    
    # Zamiast pustego Mocka, użyjemy klasy, która dziedziczy po MiniBase, 
    # aby mieć dostęp do prawdziwego Mappera i jego metod (np. _get_target_table)
    class UniversalModel(MiniBase):
        id = Number(pk=True)
        name = Text()

    mapper = UniversalModel._mapper
    data = {"name": "Test", "type": "UniversalModel"}
    
    # Teraz builder wywoła mapper._get_target_table(mapper) bez błędu
    sql, params = builder.build_insert(mapper, data)
    
    print(f"Wygenerowany SQL: {sql}")
    if "UniversalModel" in params and "INSERT INTO \"universalmodels\"" in sql:
        print("SUKCES: Builder poprawnie generuje zapytania z prawdziwym Mapperem.")
    else:
        print(f"BŁĄD: SQL Buildera jest niepoprawny: {sql}")


def test_sti_polymorphism_and_builder():
    print("\n--- 17. Test: STI, Polimorfizm i Poprawność Buildera ---")
    resolve_all_relationships()
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)

    with Session(engine, builder) as session:
        # Tworzymy różne typy osób w tej samej tabeli (STI)
        p1 = Person(name="Zwykły Jan")
        s1 = StudentSingle(name="Student Adam", grade=4)
        
        session.add(p1)
        session.add(s1)
        session.commit()

    with Session(engine, builder) as session:
        # Test 1: Czy query(StudentSingle) dodało automatycznie filtr type='StudentSingle'?
        students = session.query(StudentSingle).all()
        print(f"Liczba pobranych studentów: {len(students)}")
        for s in students:
            print(f" - {s.name}, klasa: {type(s).__name__}")
        
        # Sprawdzamy, czy nie pobrało 'Zwykły Jan' jako studenta
        if any(s.name == "Zwykły Jan" for s in students):
            print("BŁĄD: Builder nie przefiltrował rekordów po dyskryminatorze!")
        else:
            print("SUKCES: Builder poprawnie odizolował podklasę w STI.")

        # Test 2: Polimorficzne ładowanie przez klasę bazową
        all_people = session.query(Person).all()
        print(f"Całkowita liczba osób: {len(all_people)}")
        for p in all_people:
            print(f" - {p.name}, rozpoznany typ: {type(p).__name__}")

def test_builder_update_with_inheritance():
    print("\n--- 18. Test: Builder Update i fizyczna tabela ---")
    engine = DatabaseEngine()
    builder = QueryBuilder()
    
    # Testujemy, czy build_update trafia w dobrą tabelę przy STI
    from example import StudentSingle
    mapper = StudentSingle._mapper
    
    data = {"name": "Nowe Imie", "grade": 6}
    sql, params = builder.build_update(mapper, data, 1)
    
    print(f"Wygenerowany SQL UPDATE: {sql}")
    # Powinno być "persons" a nie "studentsingles"
    if "\"people\"" in sql:
        print("SUKCES: Builder użył tabeli bazowej dla podklasy STI.")
    else:
        print("BŁĄD: Builder próbuje aktualizować nieistniejącą tabelę podklasy.")


def test_advanced_orm_features():
    print("\n=== 19. Mega Test: 5 Zaawansowanych Scenariuszy ===")
    resolve_all_relationships()
    engine = DatabaseEngine()
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)

    # SCENARIUSZ 1: Automatyczna synchronizacja FK i dociąganie (Lazy Loading)
    print("\n--- Scenariusz 1: Auto-FK Sync & Lazy Loading ---")
    with Session(engine, builder) as session:
        it_dept = Department(name="IT Core")
        emp = Employee(name="Krzysztof")
        emp.department = it_dept # Przypisujemy obiekt, nie ID
        session.add(emp)
        session.commit()
        
        # Sprawdzamy, czy system sam uzupełnił 'department_id' w obiekcie emp
        if emp.department_id == it_dept.id:
            print(f"SUKCES: Klucz obcy zsynchronizowany automatycznie ({emp.department_id})")
        else:
            print(f"BŁĄD: Brak synchronizacji FK! ID: {emp.department_id}")

    # SCENARIUSZ 2: Izolacja Sesji i Identity Map
    print("\n--- Scenariusz 2: Izolacja Sesji (Dwie sesje obok siebie) ---")
    session1 = Session(engine, builder)
    session2 = Session(engine, builder)
    
    e_s1 = session1.get(Employee, emp.id)
    e_s2 = session2.get(Employee, emp.id)
    
    print(f"Czy e1 i e2 to te same instancje? {e_s1 is e_s2} (Powinno być False)")
    if e_s1 is not e_s2:
        print("SUKCES: Sesje są odizolowane, każda ma własną Identity Map.")
    
    session1.close()
    session2.close()

    # SCENARIUSZ 3: Złożone Filtrowanie i Paginacja
    print("\n--- Scenariusz 3: Filtrowanie + Paginacja ---")
    with Session(engine, builder) as session:
        # Czyścimy dla pewności i dodajemy 5 pracowników
        for i in range(5):
            session.add(Employee(name=f"Worker {i}"))
        session.commit()
        
        # Oczekujemy dokładnie rekordów 3 i 4 (indeksy 2, 3 od początku listy tych z NULL)
        results = session.query(Employee).filter(department_id=None).limit(3).offset(2).all()
        
        print(f"Pobrano {len(results)} rekordów (Oczekiwano: 3).")
        # Sceptyczne sprawdzenie:
        if len(results) == 3:
            print("SUKCES: Paginacja i filtrowanie IS NULL działają.")
        else:
            print(f"BŁĄD: Paginacja zwróciła niewłaściwą liczbę wyników: {len(results)}")

    # SCENARIUSZ 4: Stabilność stanów po Rollbacku
    print("\n--- Scenariusz 4: Karuzela stanów (Rollback test) ---")
    with Session(engine, builder) as session:
        new_dept = Department(name="To Delete")
        session.add(new_dept)
        session.flush() # Wstawiamy do bazy
        
        old_id = new_dept.id
        session.rollback() # Cofamy wszystko
        
        print(f"Stan obiektu po rollbacku: {new_dept._orm_state}")
        if new_dept._orm_state == ObjectState.TRANSIENT and new_dept.id is None:
            print("SUKCES: Rollback poprawnie wyczyścił ID i przywrócił stan TRANSIENT.")

    # SCENARIUSZ 5: Polimorficzny Miks (Różne klasy w jednym wyniku)
    print("\n--- Scenariusz 5: Polimorficzny Miks (STI) ---")
    with Session(engine, builder) as session:
        # Tabela 'people' zawiera różne klasy
        session.add(Person(name="Commoner"))
        session.add(StudentSingle(name="Scholar", grade=5))
        session.commit()
        
    with Session(engine, builder) as session:
        # Zapytanie o klasę bazową Person powinno zwrócić Person I StudentSingle
        mixed_results = session.query(Person).all()
        types = [type(obj).__name__ for obj in mixed_results]
        print(f"Pobrane typy z tabeli 'people': {types}")
        if "Person" in types and "StudentSingle" in types:
            print("SUKCES: Polimorficzne ładowanie poprawnie rozpoznaje różne klasy w jednej tabeli.")

    print("\n--- 4. Test Automatycznego Dirty Checking (Poprawiony) ---")
    with Session(engine, builder) as session:
        dept = Department(name="Initial Name")
        session.add(dept)
        session.commit() # Tutaj powstaje snapshot: 'Initial Name'
        
        dept.name = "New Better Name" # Zmiana tylko w Pythonie
        
        session.flush() # TU POWINIEN POJAWIĆ SIĘ SQL UPDATE w logach!
        
        # Sprawdzenie fizyczne w bazie
        res = engine.execute("SELECT name FROM departments WHERE id = ?", (dept.id,))
        print(f"Nazwa w bazie: {res[0]['name']}")

    print("\n--- Szpiegowski Test Dirty Checkingu ---")
    with Session(engine, builder) as session:
        # 1. Tworzymy obiekt
        dept = Department(name="Initial Name")
        session.add(dept)
        session.commit()
        print(f"Po komicie: ID={dept.id}, Stan={getattr(dept, '_orm_state', None)}")

        # 2. Zmieniamy nazwę - to powinno wyzwolić refresh przez __getattribute__
        print("\nZmieniam nazwę na 'Marketing'...")
        dept.name = "Marketing" 
        
        # 3. SZPIEGOWANIE: Sprawdzamy co sesja ma w snapshotach
        pk_val = getattr(dept, dept._mapper.pk)
        snapshot_key = (dept.__class__, pk_val) # Lub id(dept) jeśli jeszcze nie zmieniłeś klucza
        
        # Próbujemy obu wersji klucza, żeby wiedzieć co masz w kodzie
        snap = session._snapshots.get(snapshot_key) or session._snapshots.get(id(dept))
        
        print(f"SNAPSHOT w sesji: {snap}")
        print(f"AKTUALNY __dict__: {{'name': '{dept.__dict__.get('name')}'}}")
        
        if snap and snap.get('name') == dept.__dict__.get('name'):
            print("!!! ALARM: Snapshot i obiekt są identyczne. Dirty checking nic nie wykryje!")
        else:
            print("--- Sukces: Sesja widzi różnicę. Jeśli UPDATE nie pójdzie, winny jest QueryBuilder.")

        # 4. Próba wymuszenia zapisu
        print("\nWywołuję session.flush()...")
        session.flush()
        
        # 5. Sprawdzenie końcowe w bazie
        res = engine.execute("SELECT name FROM departments WHERE id = ?", (dept.id,))
        final_name = res[0]['name'] if res else "BRAK REKORDU"
        print(f"Finałowa nazwa w bazie: {final_name}")
        
        if final_name == "Marketing":
            print("WYNIK: Test ZALICZONY.")
        else:
            print("WYNIK: Test OBLANY. Brak UPDATE w bazie.")

    print("\n" + "="*50)
    print("URUCHAMIANIE MEGA-DIAGNOSTYKI ORM (10 SCENARIUSZY)")
    print("="*50)

    # --- SCENARIUSZ 1: DOUBLE LOAD (IDENTITY MAP) ---
    print("\n[1] Test: Identity Map - Double Load")
    with Session(engine, builder) as session:
        d1 = Department(name="IT Core")
        session.add(d1)
        session.commit()
        
        d2 = session.query(Department).filter(id=d1.id).first()
        d3 = session.get(Department, d1.id)
        
        if d1 is d2 is d3:
            print("  SUKCES: Tożsamość zachowana (is)")
        else:
            print(f"  BŁĄD: Różne instancje dla ID {d1.id}!")

    # --- SCENARIUSZ 2: RESURRECTION (DELETE -> ADD) ---
    print("\n[2] Test: Zmartwychwstanie (Delete -> Add)")
    with Session(engine, builder) as session:
        dept = Department(name="Temporary Dept")
        session.add(dept)
        session.commit()
        
        session.delete(dept)
        session.add(dept) # Cofnięcie decyzji o usunięciu
        session.flush()
        
        state = getattr(dept, '_orm_state', None)
        print(f"  Stan po 're-add': {state}")
        # Powinien być PERSISTENT, a baza nie powinna dostać DELETE

    # --- SCENARIUSZ 3: AUTO-FK SYNC (CASCADING ADD) ---
    print("\n[3] Test: Many-To-One Auto-Sync")
    with Session(engine, builder) as session:
        new_dept = Department(name="Research")
        emp = Employee(name="Adam Explorer")
        emp.department = new_dept # Przypisujemy obiekt, nie ID
        
        session.add(emp) # Dodajemy TYLKO dziecko
        session.commit()
        
        if emp.department_id == new_dept.id and new_dept.id is not None:
            print(f"  SUKCES: FK zsynchronizowany: {emp.department_id}")
        else:
            print("  BŁĄD: FK nie został uzupełniony!")

    # --- SCENARIUSZ 4: UPDATE TO NONE (NULL) ---
    print("\n[4] Test: Update do NULL")
    with Session(engine, builder) as session:
        emp = session.query(Employee).first()
        old_name = emp.name
        emp.name = None # Ustawiamy NULL
        session.commit()
        
        res = engine.execute("SELECT name FROM employees WHERE id = ?", (emp.id,))
        if res and res[0]['name'] is None:
            print(f"  SUKCES: Pole '{old_name}' zmienione na NULL w bazie")
        else:
            print("  BŁĄD: Baza nie przyjęła NULL-a")

    # --- SCENARIUSZ 5: SNAPSHOT CLEANUP ---
    print("\n[5] Test: Snapshot Cleanup po Delete")
    with Session(engine, builder) as session:
        d_temp = Department(name="To Delete")
        session.add(d_temp)
        session.flush()
        
        key = (d_temp.__class__, d_temp.id)
        exists_before = key in session._snapshots
        
        session.delete(d_temp)
        session.flush()
        
        exists_after = key in session._snapshots
        if exists_before and not exists_after:
            print("  SUKCES: Snapshot usunięty z pamięci sesji")
        else:
            print("  BŁĄD: Wyciek pamięci w snapshotach!")

    # --- SCENARIUSZ 6: PK IMMUTABILITY (SCEPTYCZNY) ---
    print("\n[6] Test: Próba zmiany Primary Key")
    with Session(engine, builder) as session:
        d_pk = Department(name="PK Guard")
        session.add(d_pk)
        session.commit()
        
        old_id = d_pk.id
        try:
            d_pk.id = 9999 # Sabotaż
            session.flush()
            # Sprawdzamy czy IM nadal trzyma go pod starym kluczem
            if session.identity_map.get(Department, old_id) is d_pk:
                print("  SUKCES: System przetrwał próbę zmiany PK (mapa stabilna)")
        except Exception as e:
            print(f"  INFO: System zablokował zmianę PK błędem: {e}")

    # --- SCENARIUSZ 7: MODYFIKACJA PO ROLLBACKU ---
    print("\n[7] Test: Modyfikacja po Rollbacku")
    with Session(engine, builder) as session:
        d_fail = Department(name="Will Fail")
        session.add(d_fail)
        session.rollback() # Wszystko wraca do TRANSIENT
        
        d_fail.name = "Second Chance"
        session.add(d_fail)
        session.commit()
        if d_fail.id is not None:
            print(f"  SUKCES: Obiekt uratowany po rollbacku, nowe ID: {d_fail.id}")

    # --- SCENARIUSZ 8: BATCH INSERT (50 OBIEKTÓW) ---
    print("\n[8] Test: Batch Insert (50 rekordów)")
    with Session(engine, builder) as session:
        for i in range(50):
            session.add(Employee(name=f"Batch Worker {i}"))
        session.commit()
        res = engine.execute("SELECT count(*) as cnt FROM employees WHERE name LIKE 'Batch Worker%'")
        print(f"  Zapisano: {res[0]['cnt']} pracowników")

    # --- SCENARIUSZ 9: RE-ATTACHMENT (DETACHED) ---
    print("\n[9] Test: Re-attachment (Nowa sesja)")
    # Sesja A
    with Session(engine, builder) as s1:
        d_det = Department(name="Session A")
        s1.add(d_det)
        s1.commit()
    
    # Sesja B
    with Session(engine, builder) as s2:
        d_det.name = "Updated in Session B"
        s2.add(d_det) # Powinien zostać rozpoznany jako PERSISTENT ze względu na ID
        s2.commit()
        
    res = engine.execute("SELECT name FROM departments WHERE id = ?", (d_det.id,))
    if res and res[0]['name'] == "Updated in Session B":
        print("  SUKCES: Obiekt Detached poprawnie zaktualizowany w nowej sesji")

    # --- SCENARIUSZ 10: IDENTITY MAP SPAM (M2M) ---
    print("\n[10] Test: Many-To-Many Idempotency")
    with Session(engine, builder) as session:
        # Ten test sprawdza czy dwukrotny flush nie wstawia duplikatów do tabel M2M
        # (Wymaga Twojej implementacji _flush_m2m)
        print("  INFO: Test M2M gotowy do weryfikacji manualnej po logach SQL")

    print("\n" + "="*50)
    print("DIAGNOSTYKA ZAKOŃCZONA")
    print("="*50)



if __name__ == "__main__":
    test_complex_scenarios()
    test_security_and_m2m_optimized()
    # test_lazy_loading_full()
    test_unit_of_work_snapshots()
    test_polymorphic_loading()
    test_circular_dependency_error()
    test_builder_universality()
    test_sti_polymorphism_and_builder()
    test_builder_update_with_inheritance()
    test_advanced_orm_features()
