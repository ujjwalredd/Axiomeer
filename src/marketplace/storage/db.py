from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from marketplace.settings import DATABASE_URL

# Configure connect_args based on database type
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}  # needed for SQLite with FastAPI

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
