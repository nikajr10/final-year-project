import sys
from sentence_transformers import SentenceTransformer
from app.db.session import engine, SessionLocal
from app.db.models import Base, Product
from sqlalchemy import text
from app.core.security import get_password_hash
from app.db.models import User

def init_db():
    print("⏳ Connecting to Database...")
    
    # 1. Create Tables (if they don't exist)
    # This automatically runs "CREATE TABLE products..."
    Base.metadata.create_all(bind=engine)
    print("✅ Tables Created!")

    # 2. Load the SBERT Model (The "Vector Maker")
    print("⏳ Loading AI Model (SBERT)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Model Loaded!")

    # 3. Your 10 Official Items
    items = [
        {"nep": "Chamal", "eng": "Rice", "unit": "kg"},
        {"nep": "Daal", "eng": "Lentils", "unit": "kg"},
        {"nep": "Tel", "eng": "Oil", "unit": "litre"},
        {"nep": "Chini", "eng": "Sugar", "unit": "kg"},
        {"nep": "Nun", "eng": "Salt", "unit": "packet"},
        {"nep": "Chiura", "eng": "Beaten Rice", "unit": "kg"},
        {"nep": "Maida", "eng": "Flour", "unit": "kg"},
        {"nep": "Anda", "eng": "Eggs", "unit": "piece"},
        {"nep": "Besar", "eng": "Turmeric", "unit": "packet"},
        {"nep": "Biskut", "eng": "Biscuits", "unit": "packet"},
    ]

    db = SessionLocal()
    
    try:
        # Clear old data to avoid duplicates
        db.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE;"))
        db.commit()
        print("🧹 Old data cleared.")

        print("🚀 Inserting 10 Items with Vectors...")
        
        for item in items:
            # MAGICAL STEP: Convert "Rice" + "Chamal" into a math vector
            # We combine English and Nepali so the AI understands both
            text_to_embed = f"{item['nep']} {item['eng']}"
            vector = model.encode(text_to_embed).tolist()

            new_product = Product(
                name_nepali=item['nep'],
                name_english=item['eng'],
                unit=item['unit'],
                current_stock=100.0, # Start with 100 stock for testing
                embedding=vector     # <--- Saving the AI Brain here
            )
            db.add(new_product)
        
        db.commit()
        print(f"🎉 Success! {len(items)} items inserted into the Database.")
        
        
        # --- SEED ADMIN USER ---
        print("👤 Seeding Admin User...")
        admin_user = db.query(User).filter(User.email == "user@user.com").first()
        if not admin_user:
            admin_user = User(
                username="user",
                email="user@user.com",
                hashed_password=get_password_hash("user"),
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            print("✅ Admin user seeded successfully! (user@user.com / user)")
        

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    
    
    
    