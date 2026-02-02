from xmlrpc import client
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from uuid import UUID
from service.whatsapp import notify_consultation_booked
from database import get_db
from models import ConsultationSlot, ConsultationQuestion, Consultation, User
from schemas import SlotResponse, QuestionResponse, LockSlotRequest, SubmitConsultationRequest, ConsultationResponse
from auth_utils import get_current_user
import os

import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from database import get_db
from models import ConsultationSlot, Consultation, User
from schemas import (
    SlotResponse, 
    QuestionResponse, 
    LockSlotRequest, 
    SubmitConsultationRequest, 
    ConsultationResponse
)
from auth_utils import get_current_user

# Initialize Razorpay Client
razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

router = APIRouter(
    prefix="/consultation",
    tags=["Consultation"]
)

# 1. GET AVAILABLE SLOTS (Calendar View)
@router.get("/slots", response_model=List[SlotResponse])
def get_slots(
    start_date: datetime, 
    end_date: datetime, 
    db: Session = Depends(get_db)
):
    """
    Fetch slots. Frontend sends: ?start_date=2023-10-01&end_date=2023-10-07
    """
    slots = db.query(ConsultationSlot).filter(
        ConsultationSlot.start_time >= start_date,
        ConsultationSlot.start_time <= end_date
    ).order_by(ConsultationSlot.start_time).all()
    return slots

# 2. GET DIAGNOSIS QUESTIONS
@router.get("/questions", response_model=List[QuestionResponse])
def get_questions(db: Session = Depends(get_db)):
    """
    Returns the active questions for the 'Diagnosis' step.
    """
    return db.query(ConsultationQuestion).filter(
        ConsultationQuestion.is_active == True
    ).order_by(ConsultationQuestion.order).all()

# 3. LOCK A SLOT (Step 1 of Booking)
@router.post("/lock")
def lock_slot(
    request: LockSlotRequest, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    slot = db.query(ConsultationSlot).filter(ConsultationSlot.id == request.slot_id).first()
    
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
        
    if slot.is_booked:
        raise HTTPException(status_code=400, detail="Slot already booked")
        
    # Check if currently locked by SOMEONE ELSE
    if slot.is_locked and slot.locked_at:
        # If lock is fresh (<10 mins) AND user is different
        if slot.locked_at > (datetime.utcnow() - timedelta(minutes=10)):
            if slot.locked_by_user_id != current_user.id:
                raise HTTPException(status_code=409, detail="Slot is currently being booked by someone else")

    # Lock it!
    slot.is_locked = True
    slot.locked_at = datetime.utcnow()
    slot.locked_by_user_id = current_user.id
    db.commit()
    
    return {"message": "Slot locked for 10 minutes", "expires_at": slot.locked_at + timedelta(minutes=10)}



# --- NEW: Create Razorpay Order for Consultation ---
@router.post("/create_order")
def create_consultation_order(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Creates a Razorpay order for the fixed consultation fee (₹500)."""
    amount = 500 * 100 # Convert to paise
    # FIX: Make receipt ID shorter (limit is 40 chars)
    # We take the last 12 chars of the User ID + current timestamp
    short_user_id = str(current_user.id)[-12:] 
    timestamp = int(datetime.utcnow().timestamp())
    receipt_id = f"rcpt_{short_user_id}_{timestamp}" 

    try:
        order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": receipt_id[:40], # Ensure it never exceeds 40 chars
            "notes": {"type": "consultation"}
        })
        return order    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 4. FINALIZE BOOKING (After Payment)
# --- UPDATED: Book with Real Link & Logic ---
@router.post("/book", response_model=ConsultationResponse)
def book_consultation(
    req: SubmitConsultationRequest,
    payment_id: str, # This will now be the REAL Razorpay ID from frontend
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    slot = db.query(ConsultationSlot).filter(ConsultationSlot.id == req.slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    # Use the static link from .env (Production Ready approach without OAuth)
    meeting_link = os.getenv("CONSULTATION_MEETING_LINK", "https://meet.google.com/link-pending")

    consultation = Consultation(
        user_id=current_user.id,
        slot_id=slot.id,
        status="confirmed",
        payment_id=payment_id,
        amount_paid=500.0,
        client_answers=req.answers,
        meeting_link=meeting_link 
    )
    
    slot.is_booked = True
    db.add(consultation)
    db.commit()
    db.refresh(consultation)

    # --- Manual Response Mapping ---
    return {
        "id": consultation.id,
        "booking_date": slot.start_time,
        "status": consultation.status,
        "meeting_link": consultation.meeting_link,
        "amount_paid": consultation.amount_paid,
        "expert_notes": consultation.expert_notes
    }