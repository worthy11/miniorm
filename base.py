from mapper import Mapper
from orm_types import Column
from states import ObjectState

class MiniBase:
    _registry = {}

    def __repr__(self):
        pk_val = getattr(self, self._mapper.pk, "New")
        return f"<{self.__class__.__name__}(id={pk_val})>"

    def __init__(self, **kwargs):
        from states import ObjectState
        object.__setattr__(self, '_orm_state', ObjectState.TRANSIENT)
        object.__setattr__(self, '_session', None)
        self.type = self.__class__.__name__
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        columns = {
            name: dtype
            for name, dtype in cls.__dict__.items()
            if isinstance(dtype, Column)
        }

        # Extract Meta class attributes
        meta_cls = getattr(cls, "Meta", None)
        meta_attrs = {}
        if meta_cls:
            for attr in dir(meta_cls):
                if not attr.startswith('_'):
                    meta_attrs[attr] = getattr(meta_cls, attr)
        
        cls._mapper = Mapper(cls, columns, meta_attrs)
        MiniBase._registry[cls] = cls._mapper

    def __getattribute__(self, name):
        # 1. Techniczne wyłączenia - tylko te pola, które nie mogą wyzwalać logiki ORM
        # USUNĘLIŚMY name == 'id', aby ID też mogło się odświeżać
        if name.startswith('_') or name == 'mapper_args':
            return object.__getattribute__(self, name)
        
        # 2. Pobranie stanu i sesji (używamy object.__getattribute__, by uniknąć rekurencji)
        state = object.__getattribute__(self, '_orm_state')
        session = object.__getattribute__(self, '_session')

        # 3. Logika EXPIRED (Lazy Loading danych kolumn)
        # Jeśli dane wygasły, idziemy do bazy, zanim spróbujemy je odczytać
        if state == ObjectState.EXPIRED and session:
            session.refresh(self)

        # 4. Logika Relacji (Lazy Loading powiązanych obiektów)
        mapper = object.__getattribute__(self, '_mapper')
        if name in mapper.relationships:
            # Jeśli relacja jest już w __dict__ (załadowana), zwróć ją
            if name in self.__dict__:
                return self.__dict__[name]

            # Jeśli nie ma, a mamy sesję - doładuj ją
            if session:
                rel = mapper.relationships[name]
                value = self._load_relationship(session, rel)
                object.__setattr__(self, name, value)
                return value

        # 5. Finalne pobranie wartości (z __dict__ instancji)
        val = object.__getattribute__(self, name)

        # 6. Sceptyczny bezpiecznik: 
        # Jeśli po odświeżeniu wciąż dostajemy obiekt typu Column (np. Number), 
        # to znaczy, że w bazie go nie ma lub refresh zawiódł.
        if isinstance(val, Column) and state != ObjectState.TRANSIENT:
            # Nie chcemy zwracać definicji kolumny jako wartości danych
            return None

        return val

    def _load_relationship(self, session, rel):   #To do
        from states import ObjectState
        
        if rel.r_type == "many-to-one":
            fk_val = getattr(self, rel._resolved_fk_name, None)
            return session.get(rel.remote_model, fk_val) if fk_val else None

        if rel.r_type == "one-to-many":
            return session.query(rel.remote_model).filter(**{rel._resolved_fk_name: self.id}).all()

        if rel.r_type == "many-to-many":
            return session.query(rel.remote_model).join_m2m(
                rel.association_table, 
                rel._resolved_local_key, 
                rel._resolved_remote_key, 
                self.id
            ).all()
        return None
    
    def __setattr__(self, name, value):
        object.__setattr__(self, name, value)
        if not name.startswith('_'):
            mapper = getattr(self, '_mapper', None)
            if mapper and name in mapper.columns:
                try:
                    state = object.__getattribute__(self, '_orm_state')
                    if state == ObjectState.EXPIRED:
                        object.__setattr__(self, '_orm_state', ObjectState.PERSISTENT)
                except AttributeError:
                    pass

        #TO DO: relacje many to many, one to one