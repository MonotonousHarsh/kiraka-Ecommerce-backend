from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Numeric, DateTime, JSON, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from database import Base  # Note: Removed the dot (.) for absolute import

# ==========================================
# 1. CORE & AUTH
# ==========================================

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="customer") # 'admin', 'customer'
    created_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=False)

    # --- RELATIONSHIPS (The Handshakes) ---
    addresses = relationship("UserAddress", back_populates="user")
    consultations = relationship("Consultation", back_populates="user")
    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)

class UserAddress(Base):
    __tablename__ = "user_addresses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    recipient_name = Column(String)
    phone_number = Column(String)
    street_address = Column(String)
    city = Column(String)
    state = Column(String)
    pincode = Column(String)
    country = Column(String, default="India")
    is_default = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="addresses")

# ==========================================
# 2. CATALOG (Product, Brand, Category)
# ==========================================

class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    logo_url = Column(String, nullable=True)
    
    products = relationship("Product", back_populates="brand")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    brand_id = Column(Integer, ForeignKey("brands.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    is_bundle = Column(Boolean, default=False)
    attributes = Column(JSON) 
    average_rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    shipping_info = Column(String, default="Standard Delivery (3-5 Days)")
    return_policy_type = Column(String, default="returnable")
    
    # Relationships
    brand = relationship("Brand", back_populates="products")
    category = relationship("Category", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product")
    reviews = relationship("Review", back_populates="product")
    bundle_links = relationship("BundleComponent", back_populates="parent_product", foreign_keys="BundleComponent.parent_product_id")

    @property
    def brand_name(self):
        return self.brand.name if self.brand else None
    @property
    def category_name(self):
        return self.category.name if self.category else None

class ProductVariant(Base):
    __tablename__ = "product_variants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    sku = Column(String, unique=True, index=True)
    color = Column(String)
    size = Column(String)
    price = Column(Numeric(10, 2))
    
    product = relationship("Product", back_populates="variants")
    images = relationship("ProductImage", back_populates="variant")
    inventory_items = relationship("Inventory", back_populates="variant")

    @property
    def total_stock_available(self):
        # Loop through all inventory items (Warehouse + Store) and sum the quantity
        return sum(item.quantity for item in self.inventory_items)

class ProductImage(Base):
    __tablename__ = "product_images"
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    image_url = Column(String, nullable=False)
    alt_text = Column(String)
    is_primary = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    
    variant = relationship("ProductVariant", back_populates="images")

class BundleComponent(Base):
    __tablename__ = "bundle_components"
    id = Column(Integer, primary_key=True)
    parent_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    component_product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    quantity_needed = Column(Integer, default=1)
    
    parent_product = relationship("Product", foreign_keys=[parent_product_id], back_populates="bundle_links")
    component_product = relationship("Product", foreign_keys=[component_product_id])

# ==========================================
# 3. INVENTORY & LOCATIONS
# ==========================================

class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True)
    name = Column(String) # Warehouse / Gurgaon

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    quantity = Column(Integer, default=0)
    
    variant = relationship("ProductVariant", back_populates="inventory_items")
    location = relationship("Location")

# ==========================================
# 4. CONSULTATION SYSTEM
# ==========================================

class ConsultationSlot(Base):
    __tablename__ = "consultation_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, nullable=False)
    is_booked = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    
    # --- ADD THIS NEW COLUMN ---
    locked_at = Column(DateTime, nullable=True) 
    # ---------------------------

    consultant_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    consultant = relationship("User")
    consultation = relationship("Consultation", back_populates="slot", uselist=False)

class ConsultationQuestion(Base):
    __tablename__ = "consultation_questions"
    id = Column(Integer, primary_key=True)
    question_text = Column(String, nullable=False)
    question_type = Column(String) 
    options = Column(JSON, nullable=True) 
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)

class Consultation(Base): # It might inherit from Base in your file, keep existing inheritance
    __tablename__ = "consultations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # --- FIX: Change UUID to Integer to match the Slots ---
    slot_id = Column(Integer, ForeignKey("consultation_slots.id")) 
    # ----------------------------------------------------

    status = Column(String, default="scheduled")
    payment_id = Column(String, nullable=True)
    amount_paid = Column(Float, default=0.0)
    
    # This stores the questionnaire answers as JSON
    client_answers = Column(JSON, nullable=True) 
    
    meeting_link = Column(String, nullable=True)
    expert_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="consultations")
    slot = relationship("ConsultationSlot", back_populates="consultation")
# ==========================================
# 5. COMMERCE (CART & ORDERS)
# ==========================================

class Cart(Base):
    __tablename__ = "carts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    items = relationship("CartItem", back_populates="cart")
    user = relationship("User", back_populates="cart") # This was the missing line!

class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True)
    cart_id = Column(UUID(as_uuid=True), ForeignKey("carts.id"))
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    quantity = Column(Integer, default=1)
    
    cart = relationship("Cart", back_populates="items")
    variant = relationship("ProductVariant")

class Order(Base):
    __tablename__ = "orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    status = Column(String, default="pending")
    total_amount = Column(Numeric(10, 2))
    payment_method = Column(String, default="razorpay")
    razorpay_order_id = Column(String)
    razorpay_payment_id = Column(String)
    shipping_address_snapshot = Column(JSON) 
    created_at = Column(DateTime, default=datetime.utcnow)
    
    items = relationship("OrderItem", back_populates="order")
    user = relationship("User", back_populates="orders")

class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    variant_id = Column(UUID(as_uuid=True), ForeignKey("product_variants.id"))
    
    price_at_purchase = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    return_request_status = Column(String, default="none")
    
    # Relationships
    order = relationship("Order", back_populates="items")
    variant = relationship("ProductVariant")

    # --- FIX: Add these Properties so the API can find the names ---
    @property
    def product_name(self):
        # Go from Item -> Variant -> Product -> Name
        if self.variant and self.variant.product:
            return self.variant.product.name
        return "Unknown Product"

    @property
    def variant_sku(self):
        # Go from Item -> Variant -> SKU
        if self.variant:
            return self.variant.sku
        return "Unknown SKU"
# ==========================================
# 6. CONTENT (BLOG & REVIEWS)
# ==========================================

class BlogPost(Base):
    __tablename__ = "blog_posts"
    id = Column(Integer, primary_key=True)
    slug = Column(String, unique=True, index=True) # Generated from title
    title = Column(String, nullable=False)
    content = Column(Text)
    featured_image = Column(String)
    published_at = Column(DateTime, default=datetime.utcnow)
    
    # --- UPDATED FIELDS ---
    is_published = Column(Boolean, default=False) # Default is HIDDEN
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True) # Link to User
    
    author = relationship("User") # Relationship

class Review(Base):
    __tablename__ = "reviews"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    rating = Column(Integer)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    review_image_url = Column(String, nullable=True)
    
    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")


class Wishlist(Base):
    __tablename__ = "wishlists"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref="wishlist_items")
    product = relationship("Product")



class Coupon(Base):
    __tablename__ = "coupons"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True) # e.g. "WELCOME10"
    discount_percent = Column(Integer) # e.g. 10
    is_active = Column(Boolean, default=True)


    