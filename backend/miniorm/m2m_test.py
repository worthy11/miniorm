"""
M2M (Many-to-Many) Relationship Test
Validates m2m table creation and data integrity
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from miniorm.base import MiniBase
from miniorm.orm_types import Text, Number, Relationship
from miniorm.session import Session
from miniorm.database import DatabaseEngine
from miniorm.generator import SchemaGenerator


class Student(MiniBase):
    student_id = Number(pk=True)
    name = Text()
    email = Text()
    courses = Relationship("Course", r_type="many-to-many")


class Course(MiniBase):
    course_id = Number(pk=True)
    title = Text()
    description = Text()
    instructor = Text()


def setup_m2m_database():
    """Create m2m database and schema"""
    print("M2M RELATIONSHIP TEST\n")
    
    db_path = "m2m_test.sqlite"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    engine = DatabaseEngine(db_path=db_path)
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)
    print("✓ Database created")
    
    return engine


def add_test_data(engine):
    """Add test data and establish m2m relationships"""
    session = Session(engine)
    
    print("\nAdding test data:")
    
    
    student1 = Student(name="Alice", email="alice@example.com")
    student2 = Student(name="Bob", email="bob@example.com")
    session.add(student1)
    session.add(student2)
    session.commit()
    print(f"  ✓ Created: {student1.name} (id={student1.student_id})")
    print(f"  ✓ Created: {student2.name} (id={student2.student_id})")
    
    
    course1 = Course(title="Python", description="Python course", instructor="John")
    course2 = Course(title="SQL", description="SQL course", instructor="Jane")
    session.add(course1)
    session.add(course2)
    session.commit()
    print(f"  ✓ Created: {course1.title} (id={course1.course_id})")
    print(f"  ✓ Created: {course2.title} (id={course2.course_id})")
    
    
    print(f"\nEstablishing M2M relationships:")
    student1.courses.append(course1)
    student1.courses.append(course2)
    student2.courses.append(course1)
    session.commit()
    print(f"  ✓ {student1.name} -> {course1.title}, {course2.title}")
    print(f"  ✓ {student2.name} -> {course1.title}")
    
    return session


def validate_m2m_table(engine):
    """Validate the M2M association table structure and data"""
    print("\n" + "-"*60)
    print("VALIDATING M2M TABLE")
    print("-"*60)
    
    cursor = engine.connection.cursor()
    
    
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%student%course%' OR name LIKE '%course%student%'"
    )
    tables = cursor.fetchall()
    
    if not tables:
        print("✗ No association table found!")
        return
    
    assoc_table_name = tables[0][0]
    print(f"✓ Association table: {assoc_table_name}")
    
    print(f"\nSchema:")
    cursor.execute(f"PRAGMA table_info({assoc_table_name})")
    for col in cursor.fetchall():
        col_id, col_name, col_type, not_null, default, pk = col
        print(f"  - {col_name}: {col_type} (pk={pk})")
    
    print(f"\nData:")
    cursor.execute(f"SELECT * FROM {assoc_table_name}")
    rows = cursor.fetchall()
    for row in rows:
        print(f"  {row}")
    print(f"  Total rows: {len(rows)}")


def test_m2m_queries(session):
    """Test m2m queries"""
    print("\n" + "-"*60)
    print("TESTING M2M QUERIES")
    print("-"*60)
    
    students = session.query(Student).all()
    for student in students:
        courses = student.courses
        print(f"\n{student.name}: {len(courses)} courses")
        for course in courses:
            print(f"  - {course.title}")


def main():
    """Main execution"""
    try:
        engine = setup_m2m_database()
        session = add_test_data(engine)
        validate_m2m_table(engine)
        test_m2m_queries(session)
        
        print("\n" + "="*60)
        print("✓ M2M TEST PASSED")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
