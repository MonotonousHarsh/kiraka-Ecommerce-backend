from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from database import get_db
from models import OrderItem, Order, User
from auth_utils import get_current_user

router = APIRouter(prefix="/support", tags=["Returns & Support"])

@router.post("/return/{order_item_id}")
def request_return(order_item_id: UUID, reason: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Find the item
    item = db.query(OrderItem).join(Order).filter(
        OrderItem.id == order_item_id,
        Order.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    # 2. Check policy (Example: simple check)
    if item.order.status != "delivered":
        raise HTTPException(status_code=400, detail="Cannot return item that hasn't been delivered")
        
    item.return_request_status = "requested"
    # In real life: Send email to Admin here
    db.commit()
    
    return {"message": "Return request submitted. We will contact you shortly."}