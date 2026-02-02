from database import engine
from sqlalchemy import text

def add_return_status_column():
    print("🛠 Updating 'order_items' table...")
    
    with engine.connect() as connection:
        try:
            # SQL command to add the missing column
            connection.execute(text("ALTER TABLE order_items ADD COLUMN return_request_status VARCHAR DEFAULT 'none'"))
            connection.commit()
            print("✅ Successfully added 'return_request_status' column.")
        except Exception as e:
            # If the column already exists, this might fail, which is fine.
            print(f"⚠️ Note: {e}")

if __name__ == "__main__":
    add_return_status_column()