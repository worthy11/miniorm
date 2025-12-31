from enum import Enum, auto

class ObjectState(Enum):
    TRANSIENT = auto()
    PENDING = auto()
    PERSISTENT = auto()
    DELETED = auto()
    DETACHED = auto()
    EXPIRED = auto()