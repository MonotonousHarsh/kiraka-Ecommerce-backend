from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from database import get_db
from models import User, Cart, CartItem, ProductVariant, Order, OrderItem, UserAddress, Coupon
from schemas import CartResponse, CartItemCreate, OrderCreate, OrderResponse
from auth_utils import get_current_user

from service.payment import create_razorpay_order, verify_payment_signature
from service.logistics import logistics_client
from service.whatsapp import notify_order_confirmed

router = APIRouter(
    prefix="/commerce",
    tags=["Commerce (Cart & Orders)"]
)

# ==========================================
# 1. CART MANAGEMENT HELPER
# ==========================================

def build_cart_response(cart):
    """
    Helper to manually build the NESTED response structure the frontend expects.
    Frontend expects: item.variant.product.name
    """
    cart_items_data = []
    total_price = 0.0

    if cart and cart.items:
        for item in cart.items:
            # Safety check
            if not item.variant or not item.variant.product:
                continue

            price_as_float = float(item.variant.price)
            line_price = item.quantity * price_as_float
            total_price += line_price

            # Get Images
            images_data = []
            if item.variant.images:
                for img in item.variant.images:
                    images_data.append({"image_url": img.image_url})
            
            # Default image fallback
            if not images_data:
                images_data.append({"image_url": "https://placehold.co/600?text=No+Image"})

            # --- CRITICAL FIX: Build Nested Structure ---
            cart_items_data.append({
                "id": item.id,
                "cart_id": item.cart_id,
                "variant_id": item.variant_id,
                "quantity": item.quantity,
                # Nest the Variant data
                "variant": {
                    "id": item.variant.id,
                    "price": item.variant.price,
                    "sku": item.variant.sku,
                    "size": item.variant.size,
                    "color": item.variant.color,
                    "total_stock_available": item.variant.total_stock_available,
                    "images": images_data,
                    # Nest the Product data inside Variant
                    "product": {
                        "id": item.variant.product.id,
                        "name": item.variant.product.name,
                        "description": item.variant.product.description,
                        "brand_name": item.variant.product.brand.name if item.variant.product.brand else "Generic"
                    }
                }
            })
    
    return {
        "id": cart.id if cart else None,
        "items": cart_items_data,
        "total_price": total_price
    }

# ==========================================
# 2. CART ENDPOINTS
# ==========================================

@router.get("/cart")
def get_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the current user's active cart with full nested details."""
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    return build_cart_response(cart)

@router.post("/cart/items")
def add_to_cart(
    item_in: CartItemCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Add item to cart and return the UPDATED nested cart immediately.
    """
    # 1. Get or Create Cart
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    # 2. Check Stock
    variant = db.query(ProductVariant).filter(ProductVariant.id == item_in.variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Product variant not found")
    
    if variant.total_stock_available < item_in.quantity:
        raise HTTPException(status_code=400, detail=f"Only {variant.total_stock_available} items left in stock")

    # 3. Check if item already exists
    existing_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.variant_id == item_in.variant_id
    ).first()
    
    if existing_item:
        existing_item.quantity += item_in.quantity
    else:
        new_item = CartItem(
            cart_id=cart.id, 
            variant_id=item_in.variant_id, 
            quantity=item_in.quantity
        )
        db.add(new_item)
    
    db.commit()
    db.refresh(cart) # Refresh ensures we see the new item relation
    
    # 4. Return FULL Nested Cart Response
    return build_cart_response(cart)

@router.delete("/cart/items/{item_id}")
def remove_from_cart(
    item_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Remove a specific item from the cart."""
    item = db.query(CartItem).join(Cart).filter(
        CartItem.id == item_id,
        Cart.user_id == current_user.id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    db.delete(item)
    db.commit()
    return {"message": "Item removed"}

# ==========================================
# 3. ORDER PROCESSING
# ==========================================

@router.post("/orders", response_model=OrderResponse)
def create_order(
    order_in: OrderCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Step 1 of Checkout: Turn Cart into a Pending Order.
    """
    # 1. Fetch Cart
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # 2. Calculate Initial Total
    total_amount = sum(item.quantity * item.variant.price for item in cart.items)
    
    # 3. APPLY COUPON LOGIC
    if order_in.coupon_code:
        coupon = db.query(Coupon).filter(
            Coupon.code == order_in.coupon_code, 
            Coupon.is_active == True
        ).first()
        
        if coupon:
            discount = (total_amount * coupon.discount_percent) / 100
            total_amount -= discount
            
            if total_amount < 0:
                total_amount = 0
        else:
            raise HTTPException(status_code=400, detail="Invalid or expired coupon code")

    # 4. Snapshot Address
    address = db.query(UserAddress).filter(UserAddress.id == order_in.shipping_address_id).first()
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    address_snapshot = {
        "street": address.street_address,
        "city": address.city,
        "state": address.state,
        "pincode": address.pincode,
        "phone": address.phone_number
    }

    # 5. Create Razorpay Order
    real_order_id = create_razorpay_order(amount_rupees=float(total_amount))

    # 6. Create Order in Database
    new_order = Order(
        user_id=current_user.id,
        status="pending",
        total_amount=total_amount,
        shipping_address_snapshot=address_snapshot,
        payment_method=order_in.payment_method,
        razorpay_order_id=real_order_id 
    )
    db.add(new_order)
    db.commit() 
    db.refresh(new_order)
    
    # 7. Move Items from Cart to Order
    for cart_item in cart.items:
        order_item = OrderItem(
            order_id=new_order.id,
            variant_id=cart_item.variant_id,
            quantity=cart_item.quantity,
            price_at_purchase=cart_item.variant.price 
        )
        db.add(order_item)
    
    # 8. Clear Cart
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    db.commit()
    
    return new_order

@router.post("/orders/{order_id}/verify")
def verify_payment(
    order_id: UUID,
    payment_id: str, 
    signature: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Step 2 of Checkout: Confirm Payment & Deduct Stock.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.status == "paid":
        return {"message": "Order already paid"}
        
    # 1. Security Check
    verify_payment_signature(order.razorpay_order_id, payment_id, signature)
    
    # 2. Mark as Paid
    order.status = "paid"
    order.razorpay_payment_id = payment_id
    
    # 3. DEDUCT STOCK
    for item in order.items:
        if item.variant.inventory_items:
            inventory = item.variant.inventory_items[0] 
            inventory.quantity -= item.quantity
    
    # 4. AUTO-SHIP
    try:
        shipment_info = logistics_client.create_shipment(
            order=order,
            user=current_user,
            address=order.shipping_address_snapshot
        )
        
        if shipment_info:
            order.status = "shipped"
            order.tracking_number = shipment_info.get('awb_code', 'TRACKING-PENDING')
    except Exception as e:
        print(f"Logistics Error: {e}")

    # 5. WHATSAPP NOTIFICATION
    try:
        notify_order_confirmed(
            user_name=current_user.full_name,
            phone=current_user.phone_number,
            order_id=str(order.id),
            amount=float(order.total_amount)
        )
    except Exception as e:
        print(f"WhatsApp Error: {e}")
            
    db.commit()
    
    return {
        "message": "Payment successful", 
        "tracking_number": order.tracking_number,
        "status": order.status
    }

@router.get("/orders", response_model=List[OrderResponse])
def get_my_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()