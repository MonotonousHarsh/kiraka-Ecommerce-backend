from twilio.rest import Client
import os

# Get these from Twilio Console (or leave dummy for now)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "AC_YOUR_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "YOUR_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "whatsapp:+14155238886") # Twilio Sandbox Number

# Initialize Client (Only if creds exist, else it will crash)
try:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
except:
    client = None
    print("⚠️ Twilio credentials missing. WhatsApp messages will print to console only.")

def send_whatsapp_message(to_number: str, message_body: str):
    """
    Sends a message. 
    NOTE: 'to_number' must include country code (e.g., +919999999999).
    """
    # 1. Format Number (Ensure it has whatsapp: prefix)
    # If user stored '9999999999', make it 'whatsapp:+919999999999'
    if not to_number.startswith("whatsapp:"):
        # Basic check for India code
        if not to_number.startswith("+"):
            to_number = f"+91{to_number}" # Default to India
        to_number = f"whatsapp:{to_number}"

    try:
        if client:
            message = client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                body=message_body,
                to=to_number
            )
            print(f"✅ WhatsApp sent to {to_number}: {message.sid}")
            return message.sid
        else:
            # Simulation Mode
            print(f"📡 [SIMULATION] WhatsApp to {to_number}: {message_body}")
            return "simulated_id"
            
    except Exception as e:
        print(f"❌ WhatsApp Failed: {e}")
        return None

def notify_order_confirmed(user_name: str, phone: str, order_id: str, amount: float):
    msg = (
        f"Hello {user_name}! 🌸\n"
        f"Thank you for shopping with Kiraka.\n\n"
        f"✅ Order Confirmed: #{str(order_id)[:8]}\n"
        f"💰 Amount: ₹{amount}\n\n"
        f"We will notify you when it ships!"
    )
    send_whatsapp_message(phone, msg)

def notify_consultation_booked(user_name: str, phone: str, time_str: str, meet_link: str):
    msg = (
        f"Hi {user_name}, your fitting is confirmed! 👙\n\n"
        f"📅 Time: {time_str}\n"
        f"🔗 Join Link: {meet_link}\n\n"
        f"Please have a measuring tape ready. See you soon!"
    )
    send_whatsapp_message(phone, msg)