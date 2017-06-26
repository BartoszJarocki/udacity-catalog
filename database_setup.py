from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine

Base = declarative_base()

engine = create_engine('sqlite:///catalog.db')

def init_db():
    import models
    Base.metadata.create_all(bind=engine)