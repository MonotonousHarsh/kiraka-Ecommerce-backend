import sys
import os
from datetime import datetime, timedelta, time
from sqlalchemy import text

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
from models import ConsultationSlot, User

def seed_slots():
    print("🛠 Checking Consultation Slots Schema...")
    
    # --- CRITICAL FIX: Force Drop with CASCADE ---
    # This ensures the table is deleted even if other tables link to it
    with engine.connect() as connection:
        try:
            connection.execute(text("DROP TABLE IF EXISTS consultation_slots CASCADE"))
            connection.commit()
            print("🗑️  Forcefully dropped 'consultation_slots' table.")
        except Exception as e:
            print(f"⚠️ Could not drop table: {e}")
    # ---------------------------------------------

    # Re-create the table with the new columns
    Base.metadata.create_all(bind=engine)
    print("✅ Database Schema Updated.")

    print("🛠 Generating Consultation Slots...")
    db = SessionLocal()

    # Get the Admin user (consultant) to assign these slots to
    consultant = db.query(User).filter(User.role == "admin").first()
    if not consultant:
        consultant = db.query(User).first()
        if not consultant:
            print("❌ No users found! Please run seed_content.py first.")
            return

    # Generate slots for the next 30 days
    today = datetime.utcnow().date()
    slots_created = 0

    for day_offset in range(30):
        current_date = today + timedelta(days=day_offset)
        
        # Skip Sundays
        if current_date.weekday() == 6: 
            continue

        # Define 4 slots per day
        time_options = [
            time(10, 0), # 10:00 AM
            time(12, 0), # 12:00 PM
            time(14, 0), # 02:00 PM
            time(16, 0)  # 04:00 PM
        ]

        for t in time_options:
            slot_datetime = datetime.combine(current_date, t)
            
            new_slot = ConsultationSlot(
                consultant_id=consultant.id,
                start_time=slot_datetime,
                is_booked=False,
                is_locked=False
            )
            db.add(new_slot)
            slots_created += 1

    db.commit()
    db.close()
    print(f"🎉 Successfully created {slots_created} available slots!")

if __name__ == "__main__":
    seed_slots()