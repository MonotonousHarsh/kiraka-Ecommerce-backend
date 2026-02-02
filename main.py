from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.staticfiles import StaticFiles
import os

# Import the new router
from routers import products
from routers import products, auth
from routers import products, auth, consultation  
from service.scheduler import start_scheduler  
from routers import products, auth, consultation, commerce  , users, content,webhooks,wishlist,coupons


app = FastAPI(
    title="Kiraka Consultants API",
    description="Backend for Lingerie E-commerce",
    version="1.0.0"
)


# Get the absolute path to the assets folder
assets_path = os.path.join(os.path.dirname(__file__), "assets")
# Check if directory exists, if not create it (prevents crash)
if not os.path.exists(assets_path):
    os.makedirs(assets_path)

# Mount the assets folder to the URL '/static'
app.mount("/static", StaticFiles(directory=assets_path), name="static")


# --- CORS (Crucial for React) ---
# Allows your Frontend (localhost:3000) to talk to Backend (localhost:8000)
origins = [
    "http://localhost:3000",
    "http://localhost:5173", # Vite default port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- STARTUP EVENT ---
@app.on_event("startup")
async def startup_event():
    start_scheduler()
    print("⏰ Scheduler started...")




# --- REGISTER ROUTERS ---
app.include_router(products.router)
app.include_router(auth.router) 
app.include_router(consultation.router)     
app.include_router(commerce.router)
app.include_router(users.router)
app.include_router(content.router)
app.include_router(webhooks.router)
app.include_router(wishlist.router)
app.include_router(coupons.router)


# --- STATIC FILES (For Images) ---
# This allows http://localhost:8000/assets/... to verify images exist
# Make sure you create a 'static' folder or point this to your assets
#app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return {"message": "Welcome to Kiraka Consultants API. The server is running!"}