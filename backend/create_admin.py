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

USERNAME = "admin"
PASSWORD = "admin123"
EMAIL    = "admin@hm.local"

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
db  = SessionLocal()

existing = db.query(User).filter(User.username == USERNAME).first()
if existing:
    print(f"User '{USERNAME}' already exists.")
else:
    user = User(
        username=USERNAME,
        email=EMAIL,
        hashed_password=pwd.hash(PASSWORD),
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
