from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Order

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/shiprocket")
async def shiprocket_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Shiprocket sends updates here when tracking status changes.
    """
    payload = await request.json()
    
    # Example Payload: {"awb": "123", "current_status": "DELIVERED"}
    awb = payload.get("awb")
    status = payload.get("current_status")
    
    if awb and status:
        order = db.query(Order).filter(Order.tracking_number == awb).first()
        if order:
            if status == "DELIVERED":
                order.status = "delivered"
            elif status == "RTO INITIATED":
                order.status = "cancelled"
            
            db.commit()
            print(f"Order {order.id} updated to {status}")
            
    return {"status": "ok"}