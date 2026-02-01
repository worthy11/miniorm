from .base import MiniBase
from .orm_types import Text, Number, Relationship


# Inheritance examples
class Person(MiniBase):
    class Meta:
        table_name = "people"
        discriminator = "type"
        discriminator_value = "person"
    
    id = Number(pk=True)
    name = Text()


class StudentSingle(Person):
    class Meta:
        inheritance = "single"
        discriminator_value = "student"
    
    grade = Number()


class Vehicle(MiniBase):
    class Meta:
        table_name = "vehicles"
    
    id = Number(pk=True)
    name = Text()
    wheels = Number()


class CarSingle(Vehicle):
    class Meta:
        inheritance = "single"
        discriminator_value = "car"
    
    doors = Number()


# Relationship examples
class Department(MiniBase):
    id = Number(pk=True)
    name = Text()


class Employee(MiniBase):
    id = Number(pk=True)
    name = Text()
    department = Relationship(Department, backref="employees", r_type="many-to-one")


class Project(MiniBase):
    id = Number(pk=True)
    name = Text()
    employees = Relationship(Employee, backref="project", r_type="one-to-many")


# Relationships with inheritance
class Company(MiniBase):
    class Meta:
        table_name = "companies"
    
    id = Number(pk=True)
    name = Text()


class TechCompany(Company):
    class Meta:
        inheritance = "single"
        discriminator_value = "tech_company"
    
    tech_stack = Text()


class Office(MiniBase):
    id = Number(pk=True)
    address = Text()
    company = Relationship(Company, r_type="many-to-one")


def resolve_all_relationships():
    from base import MiniBase
    for cls, mapper in MiniBase._registry.items():
        mapper._resolve_deferred_relationships()


if __name__ == "__main__":
    from base import MiniBase
    
    resolve_all_relationships()
    
    print("=== Inheritance ===")
    print(f"Person table: {Person._mapper.table_name}, columns: {list(Person._mapper.columns.keys())}")
    print(f"StudentSingle table: {StudentSingle._mapper.table_name}, columns: {list(StudentSingle._mapper.columns.keys())}")
    print(f"Vehicle table: {Vehicle._mapper.table_name}")
    print(f"CarSingle table: {CarSingle._mapper.table_name} (shares with Vehicle)")
    
    print("\n=== Relationships ===")
    print(f"Employee columns: {list(Employee._mapper.columns.keys())}")
    fks = [name for name, col in Employee._mapper.columns.items() 
           if hasattr(col, 'is_foreign_key') and col.is_foreign_key]
    print(f"Employee FKs: {fks}")
    
    print(f"\nProject relationships: {list(Project._mapper.relationships.keys())}")
    print(f"Employee has project_id FK: {'project_id' in Employee._mapper.columns}")
    
    print("\n=== Relationships with Inheritance ===")
    print(f"Company table: {Company._mapper.table_name}")
    print(f"TechCompany table: {TechCompany._mapper.table_name} (shares with Company)")
    office_fk = next((name for name, col in Office._mapper.columns.items() 
                      if hasattr(col, 'is_foreign_key') and col.is_foreign_key), None)
    if office_fk:
        fk_col = Office._mapper.columns[office_fk]
        print(f"Office FK '{office_fk}' -> {fk_col.target_table} (root table for SINGLE inheritance)")

