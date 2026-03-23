"""Run once to create the admin user: python create_admin.py"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from app.database import engine, SessionLocal, Base
from app.models import User, ColumnConfig
from app.seed_columns import seed_default_columns
from passlib.context import CryptContext

Base.metadata.create_all(bind=engine)

USERNAME = os.getenv("ADMIN_USERNAME", "admin")
PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
EMAIL    = os.getenv("ADMIN_EMAIL", "admin@hm.local")

if PASSWORD == "admin123":
    print("WARNING: Using default admin password 'admin123'. Set ADMIN_PASSWORD in .env before going to production.")

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
db  = SessionLocal()

existing = db.query(User).filter(User.username == USERNAME).first()
if existing:
    # Ensure is_admin flag is set even for pre-existing admin user
    if not existing.is_admin:
        existing.is_admin = True
        db.commit()
        print(f"User '{USERNAME}' already exists — is_admin flag set to True.")
    else:
        print(f"User '{USERNAME}' already exists.")
else:
    user = User(
        username=USERNAME,
        email=EMAIL,
        hashed_password=pwd.hash(PASSWORD),
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    seed_default_columns(db, user.id)
    print(f"Admin user created.")

db.close()
print(f"\n  Username : {USERNAME}")
print(f"  Password : {PASSWORD}")
print(f"\n  Open: http://localhost:8000\n")
