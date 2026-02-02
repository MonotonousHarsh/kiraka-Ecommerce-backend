import requests
import os
import json

# Get these from Shiprocket Panel > Settings > API
SHIPROCKET_EMAIL = os.getenv("SHIPROCKET_EMAIL", "your_email@gmail.com")
SHIPROCKET_PASSWORD = os.getenv("SHIPROCKET_PASSWORD", "your_password")

class LogisticsService:
    def __init__(self):
        self.base_url = "https://apiv2.shiprocket.in/v1/external"
        self.token = None

    def login(self):
        """Get Auth Token from Shiprocket"""
        url = f"{self.base_url}/auth/login"
        payload = {"email": SHIPROCKET_EMAIL, "password": SHIPROCKET_PASSWORD}
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            self.token = response.json().get('token')
        else:
            print("Shiprocket Login Failed")

    def create_shipment(self, order, user, address):
        """
        Push the order to Shiprocket Dashboard automatically.
        """
        if not self.token:
            self.login()

        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Prepare Order Items for Shiprocket
        order_items = []
        for item in order.items:
            order_items.append({
                "name": item.variant.product.name, # Assuming relationship exists
                "sku": item.variant.sku,
                "units": item.quantity,
                "selling_price": float(item.price_at_purchase)
            })

        payload = {
            "order_id": str(order.id),
            "order_date": order.created_at.strftime("%Y-%m-%d %H:%M"),
            "pickup_location": "Primary", # Name of your warehouse in Shiprocket
            "billing_customer_name": user.full_name,
            "billing_last_name": "",
            "billing_address": address['street'],
            "billing_city": address['city'],
            "billing_pincode": address['pincode'],
            "billing_state": address['state'],
            "billing_country": "India",
            "billing_email": user.email,
            "billing_phone": user.phone_number,
            "shipping_is_billing": True,
            "order_items": order_items,
            "payment_method": "Prepaid",
            "sub_total": float(order.total_amount),
            "length": 10, "breadth": 10, "height": 10, "weight": 0.5 # Default box size
        }

        url = f"{self.base_url}/orders/create/adhoc"
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "shipment_id": data.get('shipment_id'),
                "awb_code": data.get('awb_code'), # Tracking Number
            }
        else:
            print(f"Shiprocket Error: {response.text}")
            return None

logistics_client = LogisticsService()