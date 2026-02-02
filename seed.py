import json
import os
import sys

# Add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
# Import all models so Base.metadata knows what to create
from models import User, UserAddress, Brand, Category, Product, ProductVariant, ProductImage, Inventory, Location, Cart, Order, Consultation, Review, BlogPost

def seed_database():
    print("⚠️  WARNING: Resetting Database...")
    
    # 1. DROP ALL OLD TABLES (Fixes the 'UndefinedColumn' error)
    # This deletes the stale tables so we can build fresh ones
    Base.metadata.drop_all(bind=engine)
    print("✅ Old tables dropped.")

    # 2. CREATE NEW TABLES (With all the new columns like is_bundle)
    Base.metadata.create_all(bind=engine)
    print("✅ New Database Schema Created.")

    db = SessionLocal()
    print("🌱 Starting Database Seed...")

    try:
        # --- A. SETUP LOCATIONS ---
        locations = ["Online Warehouse", "Gurgaon Store"]
        loc_objs = {}
        for loc_name in locations:
            # We don't need to check existing, because we just dropped the DB
            new_loc = Location(name=loc_name)
            db.add(new_loc)
            db.commit() # Commit to get ID
            db.refresh(new_loc)
            loc_objs[loc_name] = new_loc
            print(f"   Created Location: {loc_name}")

        # --- B. LOAD JSON DATA ---
        # Ensure the path to json is correct
        json_path = os.path.join(os.path.dirname(__file__), "data", "initial_products.json")
        
        with open(json_path, "r") as f:
            products_data = json.load(f)

        for p_data in products_data:
            # 1. Handle Brand
            brand = db.query(Brand).filter_by(name=p_data['brand_name']).first()
            if not brand:
                brand = Brand(name=p_data['brand_name'])
                db.add(brand)
                db.commit()
                db.refresh(brand)
            
            # 2. Handle Category
            cat_name = p_data.get('category_name', 'Bras')
            category = db.query(Category).filter_by(name=cat_name).first()
            if not category:
                category = Category(name=cat_name)
                db.add(category)
                db.commit()
                db.refresh(category)

            # 3. Create Product
            new_product = Product(
                name=p_data['name'],
                description=p_data.get('description'),
                brand_id=brand.id,
                category_id=category.id,
                attributes=p_data.get('attributes', {}),
                shipping_info=p_data.get('shipping_info'),
                return_policy_type=p_data.get('return_policy_type'),
                is_bundle=p_data.get('is_bundle', False) # Now this column exists!
            )
            db.add(new_product)
            db.commit()
            db.refresh(new_product)

            print(f"   Added Product: {new_product.name}")

            # 4. Create Variants & Inventory
            for v_data in p_data['variants']:
                variant = ProductVariant(
                    product_id=new_product.id,
                    sku=v_data['sku'],
                    color=v_data['color'],
                    size=v_data['size'],
                    price=v_data['price']
                )
                db.add(variant)
                db.commit()
                db.refresh(variant)

                # Add Images
                for img in v_data.get('images', []):
                    db.add(ProductImage(
                        variant_id=variant.id,
                        image_url=img['image_url'],
                        is_primary=img.get('is_primary', False)
                    ))

                # Add Inventory (Warehouse)
                db.add(Inventory(
                    variant_id=variant.id,
                    location_id=loc_objs["Online Warehouse"].id,
                    quantity=v_data.get('initial_stock_warehouse', 0)
                ))
                
                # Add Inventory (Store)
                db.add(Inventory(
                    variant_id=variant.id,
                    location_id=loc_objs["Gurgaon Store"].id,
                    quantity=v_data.get('initial_stock_gurgaon', 0)
                ))
                
                db.commit()

        print("🎉 Seeding Complete! Database is fresh and ready.")
    
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()