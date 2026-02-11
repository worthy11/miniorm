from database import DatabaseEngine
from builder import QueryBuilder
from generator import SchemaGenerator
from session import Session
from base import MiniBase
from test_inheritance import PersonConcrete, StudentConcrete, TeacherConcrete

def run_concrete_test():
    engine = DatabaseEngine(":memory:")
    builder = QueryBuilder()
    generator = SchemaGenerator()
    
    print("--- 1. Przygotowanie Schematu CONCRETE ---")
    # Powinny powstać tabele: persons, StudentConcretes, TeacherConcretes
    generator.create_all(engine, MiniBase._registry)
    session = Session(engine, builder)

    print("\n--- 2. Zapisywanie obiektów Betonowych ---")
    s = StudentConcrete(name="Ania Beton", grade=6)
    t = TeacherConcrete(name="Pan Twardy", subject="Fizyka")
    
    session.add(s)
    session.add(t)
    session.commit()
    
    print("\n--- 3. Weryfikacja fizyczna tabel ---")
    # Sprawdzamy tabelę bazową (powinna być pusta lub mieć tylko "czyste" osoby)
    p_data = engine.execute("SELECT * FROM persons")
    print(f"Tabela 'persons': {len(p_data)} rekordów (oczekiwane 0)")
    
    # Sprawdzamy tabele dzieci
    s_data = engine.execute("SELECT * FROM StudentConcretes")
    print(f"Tabela 'StudentConcretes': {dict(s_data[0]) if s_data else 'PUSTA'}")
    
    t_data = engine.execute("SELECT * FROM TeacherConcretes")
    print(f"Tabela 'TeacherConcretes': {dict(t_data[0]) if t_data else 'PUSTA'}")

    session.identity_map.clear()

    print("\n--- 4. Test Query po Klasie Konkretnej ---")
    student = session.query(StudentConcrete).filter(grade=6).first()
    if student:
        print(f"Sukces! Pobrano studenta: {student.name} z klasy {type(student).__name__}")

    print("\n--- 5. WIELKI TEST: Polimorficzny Query po PersonConcrete ---")
    # To wywoła UNION ALL w QueryBuilder
    all_people = session.query(PersonConcrete).all()
    
    print(f"Pobrano łącznie osób: {len(all_people)} (oczekiwane 2)")
    for p in all_people:
        print(f"Osobnik: {p.name} | Klasa: {type(p).__name__}")
        if isinstance(p, StudentConcrete):
            print(f"   -> Ma ocenę: {p.grade}")
        elif isinstance(p, TeacherConcrete):
            print(f"   -> Ma przedmiot: {p.subject}")

if __name__ == "__main__":
    try:
        run_concrete_test()
    except Exception as e:
        print(f"\nBŁĄD TESTU: {e}")
        import traceback
        traceback.print_exc()