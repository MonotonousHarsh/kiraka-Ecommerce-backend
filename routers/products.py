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

@router.get("/", response_model=list) # simplified response model hint
def get_products(
    skip: int = 0,
    limit: int = 50,
    brand_id: Optional[int] = None,
    category_id: Optional[int] = None,
    # --- NEW FILTERS ---
    sub_category: Optional[str] = None,
    is_wired: Optional[bool] = None,
    is_padded: Optional[bool] = None,
    material_feature: Optional[str] = None,
    activity: Optional[str] = None,
    search: Optional[str] = None,
    # -------------------
    db: Session = Depends(get_db)
):
    query = db.query(Product)

    # 1. Basic Filters
    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    if category_id:
        query = query.filter(Product.category_id == category_id)

    # 2. Advanced Filters (Phase 2 Data)
    if sub_category:
        query = query.filter(Product.sub_category == sub_category)
    if is_wired is not None:
        query = query.filter(Product.is_wired == is_wired)
    if is_padded is not None:
        query = query.filter(Product.is_padded == is_padded)
    if material_feature:
        query = query.filter(Product.material_feature == material_feature)
    if activity:
        query = query.filter(Product.activity == activity)

    # 3. Search (Name or Description)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (Product.name.ilike(search_fmt)) | 
            (Product.description.ilike(search_fmt))
        )

    # Execute
    products = query.offset(skip).limit(limit).all()
    
    # Return formatted data (including brand/category names)
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


@router.get("/{product_id}")
def get_product_detail(product_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product