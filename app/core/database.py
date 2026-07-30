from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

Base = declarative_base()
engine=create_engine(url = settings.DB_CONNECTION)
local_session=sessionmaker(bind=engine)

def get_db():
    session = local_session()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()