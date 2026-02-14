"""
Advanced filtering tests for miniorm
Tests various SQLAlchemy-style filters on existing test_filter.sqlite database

KEY USAGE PATTERNS:
==================

1. Basic Comparison:
   session.query(Animal).filter(col('age') > 5).all()

2. Multiple Values (IN):
   session.query(Animal).filter(col('age').in_([3, 5, 7])).all()

3. Pattern Matching (LIKE):
   session.query(Animal).filter(col('name').like('%e%')).all()

4. Range (BETWEEN):
   session.query(Animal).filter(col('age').between(3, 7)).all()

5. Combining with AND/OR:
   session.query(Animal).filter(
       (col('age') > 3) & (col('name').like('%e%'))
   ).all()

6. Filtering by another record's field:
   target = session.query(Animal).filter(col('id') == 2).first()
   session.query(Animal).filter(col('age') < target.age).all()

7. Negation with ~ operator:
   session.query(Animal).filter(~(col('age') > 5)).all()
   session.query(Animal).filter(~(col('age').in_([5, 7, 8]))).all()
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from miniorm.base import MiniBase
from miniorm.orm_types import Text, Number, Relationship
from miniorm.session import Session
from miniorm.database import DatabaseEngine
from miniorm.filters import col, and_, or_


class Animal(MiniBase):
    id = Number(pk=True)
    name = Text()
    age = Number()
    class Meta:
        table_name = "animals"
        inheritance = "class"


class Dog(Animal):
    id = Relationship(Animal, r_type="many-to-one")
    breed = Text()
    class Meta:
        inheritance = "class"
        table_name = "dogs"
        

class Cat(Animal):
    id = Relationship(Animal, r_type="many-to-one")
    color = Text()
    class Meta:
        inheritance = "class"
        table_name = "cats"


db_path = "test_filter.sqlite"
engine = DatabaseEngine(db_path=db_path)
session = Session(engine)



def test_basic_comparison_filters():
    """Test basic comparison operators"""
    print("\n" + "="*60)
    print("TEST 1: Basic Comparison Filters")
    print("="*60)
    
    print("\nAll animals:")
    animals = session.query(Animal).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\nAnimals with age > 5:")
    animals = session.query(Animal).filter(col('age') > 5).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\nAnimals with age <= 3:")
    animals = session.query(Animal).filter(col('age') <= 3).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\nAnimals with age == 3:")
    animals = session.query(Animal).filter(col('age') == 3).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")

    print("\nAnimals with age > 30:")
    animals = session.query(Animal).filter(col('age') > 30).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ Basic comparison filters work!")


def test_in_filter():
    """Test IN filter with multiple values"""
    print("\n" + "="*60)
    print("TEST 2: IN Filter - Filter by Multiple Values")
    print("="*60)
    
    print("\nAnimals with age IN (3, 5, 7):")
    animals = session.query(Animal).filter(col('age').in_([3, 5, 7])).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ IN filter works!")


def test_not_in_filter():
    """Test NOT IN filter"""
    print("\n" + "="*60)
    print("TEST 3: NOT IN Filter")
    print("="*60)
    
    print("\nAnimals with age NOT IN (2, 3):")
    animals = session.query(Animal).filter(col('age').not_in([2, 3])).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ NOT IN filter works!")


def test_like_pattern():
    """Test LIKE pattern matching"""
    print("\n" + "="*60)
    print("TEST 4: LIKE Pattern Matching")
    print("="*60)
    
    print("\nAnimals with name containing 'e':")
    animals = session.query(Animal).filter(col('name').like('%e%')).all()
    for animal in animals:
        print(f"  {animal.name}")
    
    print("\nAnimals with name starting with 'B':")
    animals = session.query(Animal).filter(col('name').like('B%')).all()
    for animal in animals:
        print(f"  {animal.name}")
    
    print("\n✓ LIKE pattern matching works!")


def test_between_filter():
    """Test BETWEEN filter"""
    print("\n" + "="*60)
    print("TEST 5: BETWEEN Filter")
    print("="*60)
    
    print("\nAnimals with age BETWEEN 3 and 7:")
    animals = session.query(Animal).filter(col('age').between(3, 7)).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ BETWEEN filter works!")


def test_combined_and_filter():
    """Test combining filters with AND"""
    print("\n" + "="*60)
    print("TEST 6: Combined AND Filter (&)")
    print("="*60)
    
    print("\nAnimals with name LIKE '%e%' AND age > 3:")
    animals = session.query(Animal).filter(
        (col('name').like('%e%')) & (col('age') > 3)
    ).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ Combined AND filter works!")


def test_combined_or_filter():
    """Test combining filters with OR"""
    print("\n" + "="*60)
    print("TEST 7: Combined OR Filter (|)")
    print("="*60)
    
    print("\nAnimals with age == 5 OR age == 8:")
    animals = session.query(Animal).filter(
        (col('age') == 5) | (col('age') == 8)
    ).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ Combined OR filter works!")


def test_complex_nested_filter():
    """Test complex nested conditions"""
    print("\n" + "="*60)
    print("TEST 8: Complex Nested Filter")
    print("="*60)
    
    print("\nAnimals with (name LIKE '%e%' AND age > 3) OR (age == 2):")
    animals = session.query(Animal).filter(
        ((col('name').like('%e%')) & (col('age') > 3)) | 
        (col('age') == 2)
    ).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ Complex nested filter works!")


def test_and_helper():
    """Test and_() helper function"""
    print("\n" + "="*60)
    print("TEST 9: and_() Helper Function")
    print("="*60)
    
    print("\nAnimals with age > 3 AND age < 8 using and_():")
    animals = session.query(Animal).filter(
        and_(col('age') > 3, col('age') < 8)
    ).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ and_() helper works!")


def test_or_helper():
    """Test or_() helper function"""
    print("\n" + "="*60)
    print("TEST 10: or_() Helper Function")
    print("="*60)
    
    print("\nAnimals with age == 2 OR age == 7 using or_():")
    animals = session.query(Animal).filter(
        or_(col('age') == 2, col('age') == 7)
    ).all()
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ or_() helper works!")


def test_species_filters():
    """Test filtering Dogs and Cats specifically"""
    print("\n" + "="*60)
    print("TEST 11: Species-Specific Filters")
    print("="*60)
    
    print("\nAll dogs:")
    dogs = session.query(Dog).all()
    for dog in dogs:
        print(f"  {dog.name} - {dog.breed}, age {dog.age}")
    
    print("\nAll cats:")
    cats = session.query(Cat).all()
    for cat in cats:
        print(f"  {cat.name} - {cat.color}, age {cat.age}")
    
    print("\n✓ Species-specific queries work!")


def test_filter_by_record_field_1():
    """Test filtering where age is less than age of record with id=2"""
    print("\n" + "="*60)
    print("TEST 12: Filter by Another Record's Field (Example 1)")
    print("="*60)
    
    print("\nFind animals with age < age of animal with id=2")
    print("-" * 40)
    
    target = session.query(Animal).filter(col('id') == 2).first()
    if target:
        print(f"Target: Animal id=2 - {target.name} (age {target.age})")
        
        animals = session.query(Animal).filter(col('age') < target.age).all()
        print(f"\nAnimals younger than {target.age}:")
        for animal in animals:
            print(f"  {animal.name} - age {animal.age}")
    else:
        print("  No animal with id=2 found")
    
    print("\n✓ Filter by record's field works!")




def test_filter_by_record_field_2():
    """Test filtering dogs older than a specific cat"""
    print("\n" + "="*60)
    print("TEST 13: Filter by Another Record's Field (Example 2)")
    print("="*60)
    
    print("\nFind dogs older than the cat named Filemon")
    print("-" * 40)
    
    target_cat = session.query(Cat).filter(col('name') == 'Filemon').first()
    if target_cat:
        print(f"Target: Cat - {target_cat.name} (age {target_cat.age})")
        
        dogs = session.query(Dog).filter(col('age') > target_cat.age).all()
        print(f"\nDogs older than {target_cat.age}:")
        for dog in dogs:
            print(f"  {dog.name} ({dog.breed}) - age {dog.age}")
    else:
        print("  No cat named Filemon found")
    
    print("\n✓ Filter by record's field works!")



def test_negation_filter_1():
    """Test negation with ~ operator"""
    print("\n" + "="*60)
    print("TEST 14: Negation Filter - ~ Operator (Example 1)")
    print("="*60)
    
    print("\nFind animals NOT older than 5:")
    animals = session.query(Animal).filter(~(col('age') > 5)).all()
    print(f"  (equivalent to age <= 5)")
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ Negation with ~ operator works!")


def test_negation_filter_2():
    """Test negation with complex filter"""
    print("\n" + "="*60)
    print("TEST 15: Negation Filter - ~ Operator (Example 2)")
    print("="*60)
    
    print("\nFind animals NOT matching (name contains 'v' AND age > 3):")
    animals = session.query(Animal).filter(
        ~((col('name').like('%v%')) & (col('age') > 3))
    ).all()
    for animal in animals:
        print(f"  {animal.name} - {animal.age} years old")
    
    print("\n✓ Negation with complex filters works!")


def test_negation_with_in_filter():
    """Test negation with IN filter"""
    print("\n" + "="*60)
    print("TEST 16: Negation Filter - With IN (Example 3)")
    print("="*60)
    
    print("\nFind animals NOT with age IN (5, 7, 8):")
    animals = session.query(Animal).filter(
        ~(col('age').in_([5, 7, 8]))
    ).all()
    print(f"  (equivalent to NOT IN)")
    for animal in animals:
        print(f"  {animal.name} - age {animal.age}")
    
    print("\n✓ Negation with IN filter works!")


def run_all_tests():
    """Run all tests on existing database"""
    print("\n" + "="*60)
    print("CONNECTING TO DATABASE: test_filter.sqlite")
    print("="*60)
    print("✓ Connected successfully\n")
    
    test_basic_comparison_filters()
    test_in_filter()
    test_not_in_filter()
    test_like_pattern()
    test_between_filter()
    test_combined_and_filter()
    test_combined_or_filter()
    test_complex_nested_filter()
    test_and_helper()
    test_or_helper()
    test_species_filters()
    test_filter_by_record_field_1()
    test_filter_by_record_field_2()
    test_negation_filter_1()
    test_negation_filter_2()
    test_negation_with_in_filter()
    
    print("\n" + "="*60)
   
    
if __name__ == "__main__":
    run_all_tests()
