"""SQLAlchemy test: User has many Addresses. Insert multiple addresses for one user,
then query session.query(User).join(Address).all()"""
import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, Session, sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    nickname = Column(String)
    addresses = relationship("Address", back_populates="user")

    def __repr__(self):
        return "<User(name='%s', fullname='%s', nickname='%s')>" % (
            self.name, self.fullname, self.nickname,
        )

class Address(Base):
    __tablename__ = "addresses"
    id = Column(Integer, primary_key=True)
    email_address = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="addresses")

    def __repr__(self):
        return "<Address(email_address='%s')>" % self.email_address


def main():
    db_path = os.path.join(os.path.dirname(__file__), "test_sqlalchemy.sqlite")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        user = User(name="alice", fullname="Alice A", nickname="al")
        session.add(user)
        session.commit()

        a1 = Address(email_address="a1@example.com", user_id=user.id)
        a2 = Address(email_address="a2@example.com", user_id=user.id)
        session.add_all([a1, a2])
        session.commit()

        users = session.query(User).join(Address).all()
        print(users)
        assert len(users) == 1, f"expected 1 user, got {len(users)}"
        assert len(users[0].addresses) == 2, f"expected 2 addresses, got {len(users[0].addresses)}"
        emails = {a.email_address for a in users[0].addresses}
        assert emails == {"a1@example.com", "a2@example.com"}, f"addresses: {emails}"
        print("OK: session.query(User).join(Address).all() -> 1 user with 2 addresses")


if __name__ == "__main__":
    main()
