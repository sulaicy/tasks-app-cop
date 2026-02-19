# db_create.py
import os
from models import Base, get_engine
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///task_tracker.db')

engine = get_engine(DB_URL)
Base.metadata.create_all(engine)
print("Database created at", DB_URL)