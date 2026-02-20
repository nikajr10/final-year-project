from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# CONNECT TO: superuser | finalpassword | Port 5435 | DB final_inventory
DATABASE_URL = "postgresql://superuser:finalpassword@127.0.0.1:5435/final_inventory"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()