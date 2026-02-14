import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from miniorm.base import MiniBase
from miniorm.orm_types import Text, Number, Relationship
from miniorm.session import Session
from miniorm.database import DatabaseEngine
from miniorm.generator import SchemaGenerator



def test_class_inheritance_and_records():
    
    class Animal(MiniBase):
        id = Number(pk=True)
        name = Text()
        age = Number()
        class Meta:
            table_name = "animals"
            inheritance = "class"

    from miniorm.orm_types import ForeignKey
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


    db_path = "test_class.sqlite"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = DatabaseEngine(db_path=db_path)
    generator = SchemaGenerator()
    generator.create_all(engine, MiniBase._registry)
    session = Session(engine)

   
    
    dog = Dog(name="Burek", breed="Labrador", age=5)
    cat1 = Cat(name="Filemon", color="Czarny", age=3)
    cat2 = Cat(name="Glamzer", color="Bury", age=7)

    
    session.add(dog)
    session.add(cat1)
    session.add(cat2)
    session.commit()

   
    animals = session.query(Animal).all()
    dogs = session.query(Dog).all()
    cats = session.query(Cat).all()
    print("Animals:", animals)
    print("Dogs:", dogs)
    print("Cats:", cats)

if __name__ == "__main__":
    test_class_inheritance_and_records()
