from base import MiniBase
from orm_types import Text, Number, Relationship

class Person(MiniBase):
    class Meta:
        discriminator = "type"
        discriminator_value = "person"
    
    id = Number(pk=True)
    name = Text()

class StudentSingle(Person):
    class Meta:
        inheritance = "single"
        
    
    grade = Number()


if __name__ == "__main__":
    p = Person(id=1, name="Alice")
    s = StudentSingle(id=2, name="Bob", grade=10)

    print(p._mapper.inheritance)
    print(s._mapper.inheritance)    