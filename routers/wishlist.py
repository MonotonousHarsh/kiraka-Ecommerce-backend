from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from database import get_db
from models import Wishlist, Product, User
from auth_utils import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])

class WishlistResponse(BaseModel):
    id: UUID
    product_name: str
    product_image: str
    price: float
    product_id: UUID

@router.post("/{product_id}")
def toggle_wishlist(product_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """If item exists, remove it. If not, add it."""
    existing = db.query(Wishlist).filter(Wishlist.user_id == current_user.id, Wishlist.product_id == product_id).first()
    
    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Removed from wishlist", "active": False}
    else:
        new_item = Wishlist(user_id=current_user.id, product_id=product_id)
        db.add(new_item)
        db.commit()
        return {"message": "Added to wishlist", "active": True}

@router.get("/", response_model=list[WishlistResponse])
def get_my_wishlist(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = db.query(Wishlist).filter(Wishlist.user_id == current_user.id).all()
    
    return [{
        "id": item.id,
        "product_id": item.product.id,
        "product_name": item.product.name,
        # Naive logic: grab first variant's image and price for display
        "product_image": item.product.variants[0].images[0].image_url if item.product.variants and item.product.variants[0].images else "",
        "price": item.product.variants[0].price if item.product.variants else 0.0
    } for item in items]