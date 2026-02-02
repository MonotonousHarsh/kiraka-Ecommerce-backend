from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from database import get_db
from models import BlogPost, Review, Product, User
from schemas import BlogPostResponse, ReviewCreate, ReviewResponse
from auth_utils import get_current_user, get_current_user_optional
from fastapi import File, UploadFile, Form
import shutil
import os
from datetime import datetime
import uuid

router = APIRouter(
    prefix="/content",
    tags=["Content (Blogs & Reviews)"]
)

# ==========================================
# 1. CLIENT STORIES (BLOGS)
# ==========================================

@router.get("/blogs", response_model=List[BlogPostResponse])
def get_blogs(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Fetch published client stories."""
    return db.query(BlogPost).filter(
        BlogPost.is_published == True
    ).order_by(BlogPost.published_at.desc()).offset(skip).limit(limit).all()

@router.get("/blogs/{slug}", response_model=BlogPostResponse)
def get_blog_by_slug(slug: str, db: Session = Depends(get_db)):
    post = db.query(BlogPost).filter(BlogPost.slug == slug, BlogPost.is_published == True).first()
    if not post:
        raise HTTPException(status_code=404, detail="Story not found")
    return post

# ==========================================
# 2. PRODUCT REVIEWS
# ==========================================

@router.post("/products/{product_id}/reviews", response_model=ReviewResponse)
def add_review(
    product_id: UUID,
    review: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a review. Logic: User can review even if they haven't bought it (Amazon style),
    or you can restrict it to 'verified buyers' only by checking Orders table.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Prevent double review
    existing_review = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.product_id == product_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="You have already reviewed this product")

    new_review = Review(
        product_id=product_id,
        user_id=current_user.id,
        rating=review.rating,
        comment=review.comment,
        review_image_url=review.review_image_url
    )
    
    # Update Product Stats (Naive Average Calculation)
    # In a huge app, you'd do this in a background job
    current_total = product.average_rating * product.review_count
    product.review_count += 1
    product.average_rating = (current_total + review.rating) / product.review_count
    
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    
    # Manually construct response to include user name
    return ReviewResponse(
        user_name=current_user.full_name,
        rating=new_review.rating,
        comment=new_review.comment,
        created_at=new_review.created_at
    )

@router.get("/products/{product_id}/reviews", response_model=List[ReviewResponse])
def get_product_reviews(product_id: UUID, db: Session = Depends(get_db)):
    """Get all reviews for a product."""
    reviews = db.query(Review).filter(Review.product_id == product_id).all()
    
    # Helper to format response
    return [
        ReviewResponse(
            user_name=r.user.full_name, # Relation access
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at
        ) for r in reviews
    ]


@router.post("/stories")
def submit_story(
    title: str = Form(...),
    content: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allow users to upload their own stories.
    Status will be 'Pending' (is_published=False) by default.
    """
    # 1. Generate a Slug (URL friendly title)
    # e.g., "My Fit Journey" -> "my-fit-journey-1234"
    slug = title.lower().replace(" ", "-") + "-" + str(uuid.uuid4())[:4]

    # 2. Save the Image
    # Create directory if not exists
    upload_dir = "assets/blogs"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # Generate unique filename to prevent overwrite
    file_extension = image.filename.split(".")[-1]
    filename = f"{slug}.{file_extension}"
    file_path = f"{upload_dir}/{filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # 3. Save to Database
    new_story = BlogPost(
        title=title,
        slug=slug,
        content=content,
        featured_image=f"/assets/blogs/{filename}", # Path for frontend
        author_id=current_user.id,
        is_published=False, # <--- CRITICAL: Admin must approve this later
        published_at=datetime.utcnow()
    )
    
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    
    return {"message": "Story submitted successfully! It will be live after review."}

@router.put("/stories/{story_id}/approve")
def approve_story(
    story_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only Admin can do this
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admins can approve stories")
        
    story = db.query(BlogPost).filter(BlogPost.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
        
    story.is_published = True
    db.commit()
    
    return {"message": f"Story '{story.title}' is now LIVE."}