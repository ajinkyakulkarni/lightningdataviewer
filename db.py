from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


# variables for sqlalchemy
engine = None
db_session = None

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    github_access_token = Column(String(255))
    github_id = Column(Integer)
    github_login = Column(String(255))
    github_email = Column(String(512))

    def __init__(self, github_access_token):
        self.github_access_token = github_access_token


def init_db(app):
    # Setup sqlalchemy
    engine = create_engine(app.config['DATABASE_URI'])

    db_session = scoped_session(sessionmaker(autocommit=False,
                                             autoflush=False,
                                             bind=engine))

    Base.query = db_session.query_property()

    Base.metadata.create_all(bind=engine)
    return db_session, User
