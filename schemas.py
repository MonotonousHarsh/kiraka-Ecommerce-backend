from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from enum import Enum

# ==========================================
# 1. ENUMS & SHARED UTILS
# ==========================================

class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    STAFF = "staff"

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class ConsultationStatus(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"






# ==========================================
# 2. AUTHENTICATION & USERS
# ==========================================

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone_number: str = Field(..., description="Required for WhatsApp integration")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(UserBase):
    id: UUID
    role: str
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==========================================
# 3. ADDRESSES
# ==========================================

class AddressBase(BaseModel):
    recipient_name: str
    phone_number: str
    street_address: str
    city: str
    state: str
    pincode: str
    country: str = "India"
    is_default: bool = False

class AddressCreate(AddressBase):
    pass

class AddressResponse(AddressBase):
    id: UUID
    class Config:
        from_attributes = True

# ==========================================
# 4. CATALOG (PRODUCTS, BRANDS, IMAGES)
# ==========================================

# --- Helper Schemas ---
class BrandResponse(BaseModel):
    id: int
    name: str
    logo_url: Optional[str]
    class Config:
        from_attributes = True

class CategoryResponse(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class ImageResponse(BaseModel):
    id: int
    image_url: str
    is_primary: bool
    class Config:
        from_attributes = True

# --- Review Schema ---
class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str]
    review_image_url: Optional[str] = None

class ReviewResponse(BaseModel):
    user_name: Optional[str] = "Anonymous" # Handled in logic if user relation exists
    rating: int
    comment: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

# --- Variant Schema ---
class VariantResponse(BaseModel):
    id: UUID
    sku: str
    color: str
    size: str
    price: float
    total_stock_available: int # Calculated property from models.py
    images: List[ImageResponse] = []
    
    class Config:
        from_attributes = True

# --- Product List View (Simpler) ---
class ProductResponse(BaseModel):
    id: UUID
    name: str
    brand_name: Optional[str]
    category_name: Optional[str]
    average_rating: float
    review_count: int
    price_starts_at: Optional[float] = None # Logic can fill this or frontend can take from first variant
    
    # We include variants here so the grid can show colors
    variants: List[VariantResponse] = []
    
    class Config:
        from_attributes = True

# --- Product Detail View (Full) ---
class ProductDetailResponse(ProductResponse):
    description: Optional[str]
    shipping_info: str
    return_policy_type: str
    attributes: Dict[str, Any] = {}
    is_bundle: bool
    
    reviews: List[ReviewResponse] = []
    
    class Config:
        from_attributes = True

# ==========================================
# 5. CONSULTATION & BOOKING
# ==========================================

class SlotResponse(BaseModel):
    id: int
    start_time: datetime
   # end_time: datetime
    is_booked: bool
    is_locked: bool
    class Config:
        from_attributes = True

class QuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: str 
    options: Optional[List[str]] = None
    order: int
    class Config:
        from_attributes = True

class LockSlotRequest(BaseModel):
    slot_id: int

class SubmitConsultationRequest(BaseModel):
    slot_id: int 
    answers: Dict[str, Any]

class ConsultationResponse(BaseModel):
    id: UUID
    booking_date: Optional[datetime] # Derived from slot
    status: str
    meeting_link: Optional[str]
    amount_paid: Optional[float]
    expert_notes: Optional[str]
    class Config:
        from_attributes = True

# ==========================================
# 6. CART SYSTEM
# ==========================================

class CartItemCreate(BaseModel):
    variant_id: UUID
    quantity: int = Field(default=1, gt=0)

class CartItemUpdate(BaseModel):
    quantity: int

class CartItemResponse(BaseModel):
    id: int
    variant_id: UUID
    product_name: str = "" # We will fill this in the router or via model property
    variant_sku: Optional[str]
    price: float = 0.0
    quantity: int
    image_url: Optional[str]
    
    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    id: UUID
    items: List[CartItemResponse]
    total_price: float = 0.0
    class Config:
        from_attributes = True

# ==========================================
# 7. ORDER SYSTEM
# ==========================================

class OrderItemResponse(BaseModel):
    product_name: Optional[str] = "Processing..." # Defaults if missing
    variant_sku: Optional[str] = "N/A"
    quantity: int
    price_at_purchase: float
    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    shipping_address_id: UUID
    billing_address_id: Optional[UUID] = None 
    payment_method: str = "razorpay"
    coupon_code: Optional[str] = None

class OrderResponse(BaseModel):
    id: UUID
    created_at: datetime
    status: str
    total_amount: float
    
    # --- FIX: Make tracking_number Optional with a default ---
    tracking_number: Optional[str] = None 
    
    items: List[OrderItemResponse]
    class Config:
        from_attributes = True
# ==========================================
# 8. BLOGS
# ==========================================

class BlogPostBase(BaseModel):
    title: str
    slug: str
    content: str
    featured_image: Optional[str]
    meta_description: Optional[str]
    is_published: bool = True

class BlogPostResponse(BlogPostBase):
    id: int
    published_at: datetime
    class Config:
        from_attributes = True


