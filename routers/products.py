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
    limit: int = 12,  # Keep this low (12) for faster initial load
    brand_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    print("🚀 FAST FETCH: Starting optimized query...")
    query = db.query(Product)

    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    if category_id:
        query = query.filter(Product.category_id == category_id)

    # --- SPEED FIX ---
    # This "joinedload" instruction is what makes the query fast.
    # It fetches all related data in a single SQL query.
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