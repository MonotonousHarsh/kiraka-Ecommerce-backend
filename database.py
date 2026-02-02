import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool  # <--- IMPORT THIS
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is missing in .env file!")

# --- STABILITY FIX ---
# poolclass=NullPool disables connection pooling.
# This fixes "SSL SYSCALL error" and "Connection timed out" issues
# when working with cloud databases (Supabase) from a local machine.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=NullPool,
    connect_args={
        "options": "-c timezone=utc",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()