# from database import DatabaseEngine
# from generator import SchemaGenerator
# from base import MiniBase
# from test_inheritance import PersonSingle, StudentSingle, PersonClass, StudentClass, PersonConcrete, StudentConcrete

# def test_schema_generation():
#     engine = DatabaseEngine(":memory:")
#     generator = SchemaGenerator()
    
#     print("--- Generowanie Schematu ---")
#     generator.create_all(engine, MiniBase._registry)
    
#     def check_table(table_name):
#         print(f"\nStruktura tabeli: {table_name}")
#         info = engine.execute(f"PRAGMA table_info({table_name})")
#         for col in info:
#             print(f"  - Kolumna: {col['name']} [{col['type']}] | PK: {bool(col['pk'])}")

#     check_table("people")
#     check_table("persons")
#     check_table("StudentClasss")
#     check_table("StudentConcretes")

# if __name__ == "__main__":
#     test_schema_generation()

# from database import DatabaseEngine
# from builder import QueryBuilder
# from generator import SchemaGenerator
# from session import Session
# from base import MiniBase
# from test_inheritance import (
#     StudentSingle, StudentClass, StudentConcrete, 
#     TeacherSingle, TeacherClass, TeacherConcrete
# )

# def run_update_test():
#     engine = DatabaseEngine(":memory:")
#     builder = QueryBuilder()
#     generator = SchemaGenerator()
    
#     print("--- 1. Przygotowanie Bazy ---")
#     generator.create_all(engine, MiniBase._registry)
#     session = Session(engine, builder)

#     print("\n--- 2. Wstawianie danych początkowych ---")
#     s_single = StudentSingle(name="Edek Single", grade=3)
#     s_class = StudentClass(name="Edek Class", grade=3)
#     s_concrete = StudentConcrete(name="Edek Concrete", grade=3)
    
#     session.add(s_single)
#     session.add(s_class)
#     session.add(s_concrete)
#     session.commit()
    
#     # Czyścimy sesję, żeby mieć pewność, że dane zostaną dociągnięte z bazy
#     session.identity_map.clear()
#     s_single = session.query(StudentSingle).filter(name="Edek Single").first()
#     s_class = session.query(StudentClass).filter(name="Edek Class").first()
#     s_concrete = session.query(StudentConcrete).filter(name="Edek Concrete").first()

#     print("\n--- 3. TEST UPDATE: SINGLE (tabela 'people') ---")
#     s_single.name = "Edek S. Nowy"
#     s_single.grade = 5
#     print("Oczekiwanie: Jeden UPDATE na tabeli 'people'")
#     session.commit()

#     print("\n--- 4. TEST UPDATE: CLASS (tabele 'persons' + 'StudentClasss') ---")
#     # Zmieniamy pola w obu tabelach
#     s_class.name = "Edek C. Nowy"  # trafia do 'persons'
#     s_class.grade = 5              # trafia do 'StudentClasss'
#     print("Oczekiwanie: Dwa UPDATE-y (jeden na 'persons', drugi na 'StudentClasss')")
#     session.commit()

#     print("\n--- 5. TEST UPDATE: CONCRETE (tabela 'StudentConcretes') ---")
#     s_concrete.name = "Edek Con. Nowy"
#     s_concrete.grade = 5
#     print("Oczekiwanie: Jeden UPDATE na 'StudentConcretes'")
#     session.commit()

#     print("\n--- 6. Weryfikacja Dirty Checking (Pusty Commit) ---")
#     print("Oczekiwanie: Brak jakichkolwiek logów SQL (nic się nie zmieniło)")
#     session.commit()

# if __name__ == "__main__":
#     run_update_test()

# from database import DatabaseEngine
# from builder import QueryBuilder
# from generator import SchemaGenerator
# from session import Session
# from base import MiniBase
# from test_inheritance import StudentSingle, StudentClass, StudentConcrete

# def check_table_count(engine, table_name):
#     res = engine.execute(f'SELECT COUNT(*) FROM "{table_name}"')
#     return res[0][0] if res else 0

# def run_delete_test():
#     engine = DatabaseEngine(":memory:")
#     builder = QueryBuilder()
#     generator = SchemaGenerator()
    
#     print("--- 1. Inicjalizacja Schematu ---")
#     generator.create_all(engine, MiniBase._registry)
#     session = Session(engine, builder)

#     print("\n--- 2. Tworzenie obiektów testowych ---")
#     s_single = StudentSingle(name="Edek Single", grade=1)
#     s_class = StudentClass(name="Edek Class", grade=2)
#     s_concrete = StudentConcrete(name="Edek Concrete", grade=3)
    
#     session.add(s_single)
#     session.add(s_class)
#     session.add(s_concrete)
#     session.commit()
#     print("Baza przygotowana. Obiekty zapisane.")

#     # --- TEST SINGLE ---
#     print("\n--- 3. TEST DELETE: SINGLE (Tabela 'people') ---")
#     session.delete(s_single)
#     session.commit()
#     count = check_table_count(engine, "people")
#     print(f"Liczba rekordów w 'people' po usunięciu: {count} (Oczekiwane: 0)")

#     # --- TEST CLASS ---
#     print("\n--- 4. TEST DELETE: CLASS (Tabele 'persons' + 'StudentClasss') ---")
#     # Sprawdzamy stan przed
#     print(f"Przed usunięciem - 'persons': {check_table_count(engine, 'persons')}, 'StudentClasss': {check_table_count(engine, 'StudentClasss')}")
    
#     session.delete(s_class)
#     session.commit()
    
#     c_child = check_table_count(engine, "StudentClasss")
#     c_parent = check_table_count(engine, "persons")
#     print(f"Po usunięciu - 'StudentClasss': {c_child} (Oczekiwane 0)")
#     print(f"Po usunięciu - 'persons': {c_parent} (Oczekiwane 0)")
    
#     if c_parent == 0 and c_child == 0:
#         print("SUKCES: Strategia CLASS poprawnie wyczyściła obie tabele!")

#     # --- TEST CONCRETE ---
#     print("\n--- 5. TEST DELETE: CONCRETE (Tabela 'StudentConcretes') ---")
#     session.delete(s_concrete)
#     session.commit()
#     count = check_table_count(engine, "StudentConcretes")
#     print(f"Liczba rekordów w 'StudentConcretes' po usunięciu: {count} (Oczekiwane: 0)")

#     print("\n--- 6. Weryfikacja Stanów i Identity Map ---")
#     from states import ObjectState
#     print(f"Stan obiektu s_class po usunięciu: {getattr(s_class, '_orm_state', 'Unknown')}")
#     print(f"Czy s_class jest w Identity Map? {session.identity_map.get(StudentClass, 1) is not None}")

# if __name__ == "__main__":
#     run_delete_test()

# from database import DatabaseEngine
# from builder import QueryBuilder
# from generator import SchemaGenerator
# from session import Session
# from base import MiniBase
# from test_relationships import Owner, Pet, Visit, Procedure

# def check_m2m_count(engine, visit_id):
#     res = engine.execute('SELECT COUNT(*) FROM "procedures_visits" WHERE "visit_id" = ?', (visit_id,))
#     return res[0][0] if res else 0

# def run_complex_relation_test():
#     engine = DatabaseEngine(":memory:")
#     builder = QueryBuilder()
#     generator = SchemaGenerator()
    
#     print("--- 1. Przygotowanie Środowiska ---")
#     generator.create_all(engine, MiniBase._registry)
#     session = Session(engine, builder)

#     # Dane początkowe
#     o1 = Owner(name="Janusz", phone="111")
#     o2 = Owner(name="Grażyna", phone="222")
#     p = Pet(name="Pimpek", owner=o1)
#     proc1 = Procedure(name="Szczepienie")
#     proc2 = Procedure(name="Kontrola")
    
#     session.add(o1)
#     session.add(o2)
#     session.add(p)
#     session.add(proc1)
#     session.add(proc2)
#     session.commit()

#     print("\n--- 2. TEST UPDATE: Many-to-One (Zmiana Właściciela) ---")
#     # Zmieniamy obiekt w relacji
#     p.owner = o2
#     print("Oczekiwanie: UPDATE pets SET owner = 2 WHERE id = 1")
#     session.commit()
    
#     # Weryfikacja
#     session.identity_map.clear()
#     p_db = session.query(Pet).filter(id=p.id).first()
#     print(f"Zwierzak {p_db.name} należy teraz do ID: {getattr(p_db, 'owner', 'None')}")

#     print("\n--- 3. TEST UPDATE: Many-to-Many (Zarządzanie Procedurami) ---")
#     v = Visit(pet=p)
#     v.procedures = [proc1]
#     session.add(v)
#     session.commit()
#     print(f"Wizyta stworzona. Liczba procedur w M2M: {check_m2m_count(engine, v.id)}")

#     # DODANIE procedury do istniejącej wizyty
#     print("\nDodajemy drugą procedurę...")
#     v.procedures.append(proc2)
#     session.commit()
#     print(f"Po dodaniu - liczba w M2M: {check_m2m_count(engine, v.id)} (Oczekiwane: 2)")

#     # USUNIĘCIE jednej procedury (Test mechanizmu diff w _flush_m2m)
#     print("\nUsuwamy pierwszą procedurę...")
#     v.procedures.remove(proc1)
#     session.commit()
#     print(f"Po usunięciu - liczba w M2M: {check_m2m_count(engine, v.id)} (Oczekiwane: 1)")

#     print("\n--- 4. TEST DELETE: Many-to-Many (Czyszczenie powiązań) ---")
#     # Usuwamy wizytę - tabela asocjacyjna powinna zostać wyczyszczona dla tego ID
#     session.delete(v)
#     session.commit()
    
#     m2m_count = check_m2m_count(engine, v.id)
#     print(f"Liczba powiązań w M2M po usunięciu wizyty: {m2m_count} (Oczekiwane: 0)")
    
#     # Sprawdzamy, czy sama procedura nadal istnieje (nie powinna zniknąć!)
#     p_exists = session.query(Procedure).filter(id=proc2.id).first()
#     print(f"Czy procedura '{proc2.name}' nadal istnieje w bazie? {'Tak' if p_exists else 'Nie'}")

# if __name__ == "__main__":
#     run_complex_relation_test()



from database import DatabaseEngine
from builder import QueryBuilder
from generator import SchemaGenerator
from session import Session
from base import MiniBase
from test_relationships import Owner, Visit, Pet, Procedure
from states import ObjectState 

def run_state_test():
    engine = DatabaseEngine(":memory:")
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)
    session = Session(engine, builder)

    print("--- 1. Faza: Narodziny (TRANSIENT) ---")
    owner = Owner(name="Edek Stanowy", phone="555")
    # Sprawdzamy stan zaraz po konstruktorze
    state = getattr(owner, '_orm_state', ObjectState.TRANSIENT)
    print(f"Stan obiektu: {state} (Oczekiwane: TRANSIENT)")

    print("\n--- 2. Faza: Rejestracja (PENDING) ---")
    session.add(owner)
    state = getattr(owner, '_orm_state', 'Unknown')
    print(f"Stan po session.add: {state} (Oczekiwane: PENDING)")
    
    # Sprawdzamy czy trafił do kolejki do wstawienia
    is_in_uow = any(t.entity is owner for t in session.unit_of_work)
    print(f"Czy obiekt jest w Unit of Work? {is_in_uow}")

    print("\n--- 3. Faza: Materializacja (PERSISTENT) ---")
    session.commit()
    state = getattr(owner, '_orm_state', 'Unknown')
    print(f"Stan po commit: {state} (Oczekiwane: PERSISTENT)")
    print(f"Czy obiekt ma nadane ID? {owner.id}")
    
    # Sprawdzamy czy Identity Map go widzi
    cached_owner = session.identity_map.get(Owner, owner.id)
    print(f"Czy Identity Map trzyma ten sam obiekt? {cached_owner is owner}")

    print("\n--- 4. Faza: Aktualizacja (Wciąż PERSISTENT) ---")
    owner.name = "Edek Zmieniony"
    session.commit()
    print(f"Stan po update i commit: {getattr(owner, '_orm_state', 'Unknown')}")

    print("\n--- 5. Faza: Śmierć (DELETED) ---")
    session.delete(owner)
    # Przed flushem stan może być jeszcze PERSISTENT lub specjalny PENDING_DELETE
    print(f"Stan po delete(), ale przed commit: {getattr(owner, '_orm_state', 'Unknown')}")
    
    session.commit()
    state = getattr(owner, '_orm_state', 'Unknown')
    print(f"Stan po commit usunięcia: {state} (Oczekiwane: DELETED)")
    
    # Weryfikacja czy zniknął z mapy tożsamości
    print(f"Czy zniknął z Identity Map? {session.identity_map.get(Owner, owner.id) is None}")


    
def run_advanced_states_test():
    engine = DatabaseEngine(":memory:")
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)
    session = Session(engine, builder)

    print("--- 1. TEST: EXPIRED po Commit ---")
    owner = Owner(name="Edek Nowoczesny", phone="777")
    session.add(owner)
    session.commit()
    
    state = getattr(owner, '_orm_state', 'Unknown')
    print(f"Stan po commit: {state} (Oczekiwane: EXPIRED)")

    print("\n--- 2. TEST: DETACHED po close() ---")
    # Sprawdzamy czy przed zamknięciem ma sesję
    print(f"Czy obiekt ma sesję przed close? {getattr(owner, '_session', None) is not None}")
    
    session.close()
    
    state = getattr(owner, '_orm_state', 'Unknown')
    print(f"Stan po session.close(): {state} (Oczekiwane: DETACHED)")
    print(f"Czy obiekt ma przypisaną sesję? {getattr(owner, '_session', None) is not None}")
    
    # Weryfikacja mapy tożsamości
    print(f"Czy Identity Map jest pusta? {len(session.identity_map._map) == 0}")

    print("\n--- 3. TEST: Re-attachment (Opcjonalnie) ---")
    # Gdybyśmy chcieli wrócić, wystarczy session.add()
    session.add(owner)
    print(f"Stan po ponownym session.add(): {getattr(owner, '_orm_state', 'Unknown')} (Oczekiwane: PENDING)")


def test_lazy_loading_magic():
    engine = DatabaseEngine(":memory:")
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)
    session = Session(engine, builder)

    # 1. Tworzymy strukturę
    owner = Owner(name="Janusz", phone="123")
    pet = Pet(name="Pimpek", owner=owner)
    visit = Visit(pet=pet)
    proc = Procedure(name="Szczepienie")
    
    session.add(owner)
    session.add(pet)
    session.add(visit)
    session.add(proc)
    session.commit() # Wszystko staje się EXPIRED

    # Czyścimy mapę, żeby wymusić dociąganie z bazy
    session.identity_map.clear()

    print("\n--- TEST: Lazy Loading Many-to-One ---")
    p = session.query(Pet).first()
    print(f"Pobrano zwierzaka: {p.name}")
    # Tu powinien pójść automatyczny SELECT o ownera!
    owner_name = p.owner.name 
    print(f"Właścicielem Pimpka jest: {owner_name}")

    print("\n--- TEST: Lazy Loading Many-to-Many ---")
    v = session.query(Visit).first()
    # Dodajemy procedurę (M2M) i commitujemy
    v.procedures.append(proc)
    session.commit()
    
    # Odczytujemy po commicie
    print(f"Liczba procedur podczas wizyty: {len(v.procedures)}")

def test_transaction_rollback():
    engine = DatabaseEngine(":memory:") # Czysta baza w pamięci
    builder = QueryBuilder()
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)
    session = Session(engine, builder)

    engine.execute('CREATE UNIQUE INDEX idx_owner_phone ON owners(phone)')

    print("--- TEST: Prawdziwa Atomowość (Błąd Unikalności) ---")
    
    o1 = Owner(name="Edek Pierwszy", phone="111")
    o2 = Owner(name="Edek Duplikat", phone="111") # TEN SAM TELEFON!

    session.add(o1)
    session.add(o2)

    try:
        session.commit()
    except Exception as e:
        print(f"ZŁAPANO BŁĄD: {e}")
        session.rollback()

    # Weryfikacja
    count = engine.execute('SELECT COUNT(*) FROM "people"')[0][0]
    print(f"Liczba osób w bazie: {count} (Oczekiwane: 0)")

    print("\n--- TEST: Stan po katastrofie ---")
    print(f"Czy Edek Pierwszy ma ID? {o1.id}")
    print(f"Stan Edka w Pythonie: {getattr(o1, '_orm_state', 'Unknown')}")
    
    # Najważniejsze: czy sesja go wciąż śledzi?
    in_map = session.identity_map.get(Owner, o1.id) is not None
    print(f"Czy sesja wciąż ma go w mapie? {in_map} (Oczekiwane: False)")
    
    print(f"Liczba zadań w UoW: {len(session.unit_of_work)} (Oczekiwane: 0)")


if __name__ == "__main__":
    run_state_test()
    run_advanced_states_test()
    test_lazy_loading_magic()
    test_transaction_rollback()