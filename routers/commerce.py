from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from datetime import datetime

from database import get_db
from models import User, Cart, CartItem, ProductVariant, Order, OrderItem, UserAddress
from schemas import CartResponse, CartItemCreate, OrderCreate, OrderResponse
from auth_utils import get_current_user

from service.payment import create_razorpay_order, verify_payment_signature
from service.logistics import logistics_client
from models import User, Cart, CartItem, ProductVariant, Order, OrderItem, UserAddress, Coupon # <--- Add Coupon
from service.payment import create_razorpay_order
from service.whatsapp import notify_order_confirmed

router = APIRouter(
    prefix="/commerce",
    tags=["Commerce (Cart & Orders)"]
)

# ==========================================
# 1. CART MANAGEMENT
# ==========================================

@router.get("/cart", response_model=CartResponse)
def get_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the current user's active cart."""
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    
    # --- FIX START: Manually build the response list ---
    cart_items_data = []
    total_price = 0.0

    for item in cart.items:
        price_as_float = float(item.variant.price)
        # Calculate price for this line item
        line_price = item.quantity * price_as_float
        total_price += line_price

        # Logic to find the best image (Variant specific -> Product default -> Placeholder)
        image_url = "https://placehold.co"
        if item.variant.images and len(item.variant.images) > 0:
            image_url = item.variant.images[0].image_url
        
        # Create a dictionary that MATCHES your CartItem schema
        cart_items_data.append({
            "id": item.id,
            "cart_id": item.cart_id,
            "variant_id": item.variant_id,
            "quantity": item.quantity,
            # Flattening the nested data:
            "product_name": item.variant.product.name,
            "variant_sku": item.variant.sku,      # <--- The missing field
            "variant_price": item.variant.price,
            "image_url": image_url                # <--- The missing field
        })
    # --- FIX END ---
    
    return {
        "id": cart.id,
        "items": cart_items_data,
        "total_price": total_price
    }

@router.post("/cart/items")
def add_to_cart(
    item_in: CartItemCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Add item to cart. Handles existing items by increasing quantity."""
    # 1. Get or Create Cart
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        db.commit()
    
    # 2. Check Stock
    variant = db.query(ProductVariant).filter(ProductVariant.id == item_in.variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Product variant not found")
    
    if variant.total_stock_available < item_in.quantity:
        raise HTTPException(status_code=400, detail=f"Only {variant.total_stock_available} items left in stock")

    # 3. Check if item already exists in cart
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
    return {"message": "Item added to cart"}

@router.delete("/cart/items/{item_id}")
def remove_from_cart(
    item_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Remove a specific item from the cart."""
    # We join with Cart to ensure user only deletes THEIR OWN items
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
# 2. ORDER PROCESSING
# ==========================================

# @router.post("/orders", response_model=OrderResponse)
# def create_order(
#     order_in: OrderCreate, 
#     db: Session = Depends(get_db), 
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Step 1 of Checkout: Turn Cart into a Pending Order.
#     """
#     # 1. Fetch Cart
#     cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
#     if not cart or not cart.items:
#         raise HTTPException(status_code=400, detail="Cart is empty")

#     # 2. Calculate Total (Securely)
#     total_amount = sum(item.quantity * item.variant.price for item in cart.items)

    
    
#     # 3. Snapshot Address (So if user moves, old order history stays correct)
#     address = db.query(UserAddress).filter(UserAddress.id == order_in.shipping_address_id).first()
#     if not address:
#         raise HTTPException(status_code=404, detail="Address not found")
    
#     address_snapshot = {
#         "street": address.street_address,
#         "city": address.city,
#         "state": address.state,
#         "pincode": address.pincode,
#         "phone": address.phone_number
#     }


#     # --- CHANGED: Use Real Razorpay ---
#     real_order_id = create_razorpay_order(amount_rupees=total_amount)
        

#     # 4. Create Order
#     new_order = Order(
#         user_id=current_user.id,
#         status="pending",
#         total_amount=total_amount,
#         shipping_address_snapshot=address_snapshot,
#         payment_method=order_in.payment_method,
#         # In real life, you call Razorpay API here to get an order_id
#        razorpay_order_id=real_order_id # Storing the REAL ID
#     )
#     db.add(new_order)
#     db.commit() # Commit to get Order ID
    
#     # 5. Move Items from Cart to Order
#     for cart_item in cart.items:
#         order_item = OrderItem(
#             order_id=new_order.id,
#             variant_id=cart_item.variant_id,
#             quantity=cart_item.quantity,
#             price_at_purchase=cart_item.variant.price # Snapshot price
#         )
#         db.add(order_item)
    
#     # 6. Clear Cart
#     db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
#     db.commit()
#     db.refresh(new_order)
    
#     return new_order

@router.post("/orders", response_model=OrderResponse)
def create_order(
    order_in: OrderCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Step 1 of Checkout: Turn Cart into a Pending Order.
    Includes Coupon Calculation and Razorpay Order Generation.
    """
    # 1. Fetch Cart
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # 2. Calculate Initial Total
    # (Sum of Price * Quantity for all items)
    total_amount = sum(item.quantity * item.variant.price for item in cart.items)
    
    # 3. APPLY COUPON LOGIC (The New Part)
    if order_in.coupon_code:
        coupon = db.query(Coupon).filter(
            Coupon.code == order_in.coupon_code, 
            Coupon.is_active == True
        ).first()
        
        if coupon:
            # Calculate discount (e.g., 10% of 5000 = 500)
            discount = (total_amount * coupon.discount_percent) / 100
            total_amount -= discount
            
            # Safety check: Total cannot be negative
            if total_amount < 0:
                total_amount = 0
        else:
            # Optional: Fail if code is invalid, or just ignore it. 
            # Here we raise an error to let the user know their code failed.
            raise HTTPException(status_code=400, detail="Invalid or expired coupon code")

    # 4. Snapshot Address 
    # (So if user moves, old order history stays correct)
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

    # 5. Create Razorpay Order (With Discounted Price)
    # Note: We convert Decimal/Float to standard float for the service
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
    db.commit() # Commit to generate the Order ID
    db.refresh(new_order)
    
    # 7. Move Items from Cart to Order
    for cart_item in cart.items:
        order_item = OrderItem(
            order_id=new_order.id,
            variant_id=cart_item.variant_id,
            quantity=cart_item.quantity,
            # Snapshot price at moment of purchase
            price_at_purchase=cart_item.variant.price 
        )
        db.add(order_item)
    
    # 8. Clear Cart (Shopping is done)
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
        
    # 1. Security Check (Throws exception if invalid)
    verify_payment_signature(order.razorpay_order_id, payment_id, signature)
    
    # 2. Mark as Paid
    order.status = "paid"
    order.razorpay_payment_id = payment_id
    
    # 3. DEDUCT STOCK
    for item in order.items:
        # Safety Check: Ensure inventory records exist before accessing [0]
        if item.variant.inventory_items:
            inventory = item.variant.inventory_items[0] 
            inventory.quantity -= item.quantity
    
    # 4. AUTO-SHIP (The "Magic" Step)
    # CRITICAL FIX: This must be OUTSIDE the 'for' loop
    shipment_info = logistics_client.create_shipment(
        order=order,
        user=current_user,
        address=order.shipping_address_snapshot
    )
    
    if shipment_info:
        order.status = "shipped" # Auto-move to shipped
        order.tracking_number = shipment_info['awb_code']

# --- 5. WHATSAPP NOTIFICATION (NEW) ---
    notify_order_confirmed(
        user_name=current_user.full_name,
        phone=current_user.phone_number,
        order_id=str(order.id),
        amount=float(order.total_amount)
    )
            
    db.commit()
    
    return {
        "message": "Payment successful", 
        "tracking_number": order.tracking_number,
        "status": order.status
    }

@router.get("/orders", response_model=List[OrderResponse])
def get_my_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()