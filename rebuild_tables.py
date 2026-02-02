# backend/rebuild_tables.py
from database import engine, Base
# Import all models so SQLAlchemy knows they exist
from models import User, Brand, Category, Product, ProductVariant, ProductImage, Inventory

def rebuild():
    print("🏗️  Building Database Tables...")
    # This magic line creates all tables defined in models.py
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")

if __name__ == "__main__":
    rebuild()