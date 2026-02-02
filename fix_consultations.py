from database import engine, Base
from sqlalchemy import text

def fix_table():
    print("🗑️  Dropng 'consultations' table...")
    with engine.connect() as connection:
        try:
            connection.execute(text("DROP TABLE IF EXISTS consultations CASCADE"))
            connection.commit()
            print("✅ Table dropped.")
        except Exception as e:
            print(f"⚠️ Error: {e}")

    print("🏗️  Re-creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Done! You can now book consultations.")

if __name__ == "__main__":
    fix_table()