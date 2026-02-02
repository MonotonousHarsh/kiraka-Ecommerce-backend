import razorpay
import os
import hmac
import hashlib
from fastapi import HTTPException

# Load Razorpay credentials from environment variables
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_YOUR_KEY_HERE")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "YOUR_SECRET_HERE")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_razorpay_order(amount_rupees: float, currency: str = "INR"):
    """
    Tells Razorpay: "I am about to take 5000 Rupees. Give me an Order ID."
    """
    try:
        data = {
            "amount": int(amount_rupees * 100), # Amount in PAISA (Critical!)
            "currency": currency,
            "payment_capture": 1 # Auto-capture
        }
        order = client.order.create(data=data)
        return order['id']
    except Exception as e:
        print(f"Razorpay Error: {e}")
        raise HTTPException(status_code=500, detail="Payment Gateway Error")

def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Security Check: Ensures the user didn't hack the frontend response.
    """
    msg = f"{razorpay_order_id}|{razorpay_payment_id}"
    
    generated_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        msg.encode(),
        hashlib.sha256
    ).hexdigest()
    
    if generated_signature != razorpay_signature:
        raise HTTPException(status_code=400, detail="Invalid Payment Signature")
    return True