from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# every model inherits from this so alembic and sqlalchemy both know they exist
Base = declarative_base()


def get_db():
    # fastapi dependency: hands out a session, then always closes it,
    # even if the request blows up halfway through
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()