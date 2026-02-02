from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from database import get_db
from models import Product, ProductVariant, ProductImage, Category, Brand
from schemas import ProductResponse, ProductDetailResponse


router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

@router.get("/", response_model=List[ProductResponse])
def get_products(
    skip: int = 0, 
    limit: int = 12,
    brand_id: Optional[int] = None,
    category_id: Optional[str] = None,  # <--- CHANGED: Accept 'str' instead of 'int'
    db: Session = Depends(get_db)
):
    print("🚀 FAST FETCH: Starting optimized query...")
    query = db.query(Product)

    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    
    if category_id:
        # LOGIC: Check if input is a specific ID (number) or a Category Name (text)
        if category_id.isdigit():
            # It's an ID (e.g., category_id=1)
            query = query.filter(Product.category_id == int(category_id))
        else:
            # It's a Name (e.g., category_id=bras)
            # We join the Category table to find products with that category name
            # .ilike makes it case-insensitive (Bras == bras)
            query = query.join(Category).filter(Category.name.ilike(f"{category_id}"))

    # --- SPEED FIX (Kept from before) ---
    products = query.options(
        joinedload(Product.brand),
        joinedload(Product.category),
        joinedload(Product.variants).joinedload(ProductVariant.images)
    ).offset(skip).limit(limit).all()

    return products

@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product_detail(product_id: str, db: Session = Depends(get_db)):
    # Same optimization for the detail view
    product = db.query(Product).options(
        joinedload(Product.brand),
        joinedload(Product.category),
        joinedload(Product.variants).joinedload(ProductVariant.images),
        joinedload(Product.reviews)
    ).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product

   

# 3. GET BRANDS (For Filter Menu)
@router.get("/utils/brands")
def get_brands(db: Session = Depends(get_db)):
    return db.query(Brand).all()

# 4. GET CATEGORIES (For Navbar)
@router.get("/utils/categories")
def get_categories(db: Session = Depends(get_db)):
    return db.query(Category).all()