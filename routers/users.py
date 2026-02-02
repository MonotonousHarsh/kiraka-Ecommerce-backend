from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from database import get_db
from models import User, UserAddress
from schemas import AddressCreate, AddressResponse, UserResponse
from auth_utils import get_current_user

router = APIRouter(
    prefix="/users",
    tags=["User Profile & Addresses"]
)

# ==========================================
# 1. ADDRESS MANAGEMENT (Crucial for Checkout)
# ==========================================

@router.post("/addresses", response_model=AddressResponse)
def create_address(
    address: AddressCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Save a new shipping address.
    If this is the first address, make it default automatically.
    """
    # Check if this is the first address
    existing_count = db.query(UserAddress).filter(UserAddress.user_id == current_user.id).count()
    is_first = (existing_count == 0)

    new_address = UserAddress(
        user_id=current_user.id,
        recipient_name=address.recipient_name,
        phone_number=address.phone_number,
        street_address=address.street_address,
        city=address.city,
        state=address.state,
        pincode=address.pincode,
        country=address.country,
        is_default=address.is_default or is_first # Force default if first
    )
    
    # If new one is default, unset others
    if new_address.is_default and not is_first:
        db.query(UserAddress).filter(UserAddress.user_id == current_user.id).update({"is_default": False})
    
    db.add(new_address)
    db.commit()
    db.refresh(new_address)
    return new_address

@router.get("/addresses", response_model=List[AddressResponse])
def get_my_addresses(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """List all saved addresses for the checkout dropdown."""
    return db.query(UserAddress).filter(UserAddress.user_id == current_user.id).all()

@router.delete("/addresses/{address_id}")
def delete_address(
    address_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id, 
        UserAddress.user_id == current_user.id
    ).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
        
    db.delete(address)
    db.commit()
    return {"message": "Address deleted"}

# ==========================================
# 2. PROFILE MANAGEMENT
# ==========================================

@router.put("/profile", response_model=UserResponse)
def update_profile(
    full_name: str = None,
    phone_number: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update basic profile details."""
    if full_name:
        current_user.full_name = full_name
    if phone_number:
        # Check if phone is taken by someone else
        existing = db.query(User).filter(User.phone_number == phone_number).first()
        if existing and existing.id != current_user.id:
             raise HTTPException(status_code=400, detail="Phone number already in use")
        current_user.phone_number = phone_number
    
    db.commit()
    db.refresh(current_user)
    return current_user