from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- THIS IS THE LINE YOU ASKED FOR ---
from app.core.config import settings 

# We now pass the secure, dynamically loaded variable into the database engine
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()