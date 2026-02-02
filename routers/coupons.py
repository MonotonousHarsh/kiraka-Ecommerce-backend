# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from database import get_db
# from models import Coupon

# router = APIRouter(prefix="/coupons", tags=["Coupons"])

# @router.post("/verify/{code}")
# def verify_coupon(code: str, db: Session = Depends(get_db)):
#     coupon = db.query(Coupon).filter(Coupon.code == code, Coupon.is_active == True).first()
#     if not coupon:
#         raise HTTPException(status_code=404, detail="Invalid coupon")
#     return {"code": coupon.code, "discount_percent": coupon.discount_percent}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import Coupon
from auth_utils import get_current_user, User

router = APIRouter(
    prefix="/coupons",
    tags=["Coupons"]
)

@router.get("/verify/{code}")
def verify_coupon(code: str, db: Session = Depends(get_db)):
    """
    Check if a coupon exists and is valid.
    """
    coupon = db.query(Coupon).filter(Coupon.code == code.upper(), Coupon.is_active == True).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Invalid coupon code")
    
    # You could add more checks here (expiration date, min order value, etc.)
    
    return {
        "id": coupon.id,
        "code": coupon.code,
        "discount": coupon.discount_percent
    }