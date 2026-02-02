from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path to find database/models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import ConsultationSlot

scheduler = AsyncIOScheduler()

def unlock_stale_slots():
    """
    Checks for slots that were locked > 10 minutes ago but NOT booked.
    Releases them so other users can book.
    """
    db: Session = SessionLocal()
    try:
        # Define "Stale" (Older than 10 mins)
        ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
        
        # Find slots that are LOCKED but NOT BOOKED
        stale_slots = db.query(ConsultationSlot).filter(
            ConsultationSlot.is_locked == True,
            ConsultationSlot.is_booked == False,
            ConsultationSlot.locked_at < ten_mins_ago
        ).all()
        
        if stale_slots:
            print(f"🧹 Cleaning up {len(stale_slots)} stale slots...")
            for slot in stale_slots:
                slot.is_locked = False
                slot.locked_at = None
                slot.locked_by_user_id = None
            
            db.commit()
    except Exception as e:
        print(f"Error in scheduler: {e}")
    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(unlock_stale_slots, "interval", seconds=60)
    scheduler.start()