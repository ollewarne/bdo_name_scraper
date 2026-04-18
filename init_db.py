from sqlalchemy import create_engine
from models import Base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(DATABASE_URL)

try:
    Base.metadata.create_all(engine)
    print("tables created")
except Exception as e:
    print(f"failed to create tables: {e}")
