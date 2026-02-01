from base import MiniBase
from orm_types import Text, Number
from mapper import Mapper

class A(MiniBase):
    class Meta:
        table_name = "tabela_a"
        discriminator = "type"
        discriminator_value = "base"
    
    id = Number(pk=True)
    attr_a = Text()

class B(A):
    class Meta:
        inheritance = "SINGLE"
        discriminator_value = "sub_b"
    
    attr_b = Text()

class C(A):
    class Meta:
        inheritance = "SINGLE"
        discriminator_value = "sub_c"
    
    attr_c = Number()

def run_inheritance_test():
    print("--- Weryfikacja Kolumn w Hierarchii SINGLE ---")
    
    mapper_a = A._mapper
    
    print(f"Klasa A (Root) table: {mapper_a.table_name}")
    print(f"Kolumny w A: {list(mapper_a.columns.keys())}")
    
    has_b = 'attr_b' in mapper_a.columns
    has_c = 'attr_c' in mapper_a.columns
    
    if has_b and has_c:
        print("\n✅ SUKCES: Klasa A poprawnie zagregowała kolumny od B i C!")
    else:
        print("\n❌ BŁĄD: Klasa A nie widzi kolumn swoich dzieci.")
        if not has_b: print("   Missing: attr_b")
        if not has_c: print("   Missing: attr_c")

if __name__ == "__main__":
    run_inheritance_test()