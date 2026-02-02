# import json
# from sqlalchemy.orm import Session
# from backend.schemas import SessionLocal, engine, Base
# from backend.models import Brand, Category, Product, ProductVariant, ProductImage, Inventory, Location

# # 1. Create Tables
# Base.metadata.create_all(bind=engine)

# def seed_database():
#     db = SessionLocal()
    
#     print("🌱 Starting Database Seed...")

#     # --- A. SETUP LOCATIONS ---
#     locations = ["Online Warehouse", "Gurgaon Store"]
#     loc_objs = {}
#     for loc_name in locations:
#         existing = db.query(Location).filter_by(name=loc_name).first()
#         if not existing:
#             new_loc = Location(name=loc_name)
#             db.add(new_loc)
#             db.commit()
#             loc_objs[loc_name] = new_loc
#             print(f"Created Location: {loc_name}")
#         else:
#             loc_objs[loc_name] = existing

#     # --- B. LOAD JSON DATA ---
#     with open("data/initial_products.json", "r") as f:
#         products_data = json.load(f)

#     for p_data in products_data:
#         # 1. Handle Brand
#         brand = db.query(Brand).filter_by(name=p_data['brand_name']).first()
#         if not brand:
#             brand = Brand(name=p_data['brand_name'])
#             db.add(brand)
#             db.commit()
        
#         # 2. Handle Category
#         cat_name = p_data.get('category_name', 'Bras')
#         category = db.query(Category).filter_by(name=cat_name).first()
#         if not category:
#             category = Category(name=cat_name)
#             db.add(category)
#             db.commit()

#         # 3. Create Product
#         # Check if exists to avoid duplicates
#         existing_product = db.query(Product).filter_by(name=p_data['name']).first()
#         if existing_product:
#             print(f"Skipping {p_data['name']} (Already exists)")
#             continue

#         new_product = Product(
#             name=p_data['name'],
#             description=p_data.get('description'),
#             brand_id=brand.id,
#             category_id=category.id,
#             attributes=p_data.get('attributes', {}),
#             shipping_info=p_data.get('shipping_info'),
#             return_policy_type=p_data.get('return_policy_type')
#         )
#         db.add(new_product)
#         db.commit() # Commit to get the Product ID (UUID)

#         print(f"✅ Added Product: {new_product.name}")

#         # 4. Create Variants & Inventory
#         for v_data in p_data['variants']:
#             variant = ProductVariant(
#                 product_id=new_product.id,
#                 sku=v_data['sku'],
#                 color=v_data['color'],
#                 size=v_data['size'],
#                 price=v_data['price']
#             )
#             db.add(variant)
#             db.commit() # Commit to get Variant ID

#             # Add Images
#             for img in v_data.get('images', []):
#                 db.add(ProductImage(
#                     variant_id=variant.id,
#                     image_url=img['image_url'],
#                     is_primary=img.get('is_primary', False)
#                 ))

#             # Add Inventory (The Warehouse)
#             db.add(Inventory(
#                 variant_id=variant.id,
#                 location_id=loc_objs["Online Warehouse"].id,
#                 quantity=v_data.get('initial_stock_warehouse', 0)
#             ))
            
#             # Add Inventory (The Store)
#             db.add(Inventory(
#                 variant_id=variant.id,
#                 location_id=loc_objs["Gurgaon Store"].id,
#                 quantity=v_data.get('initial_stock_gurgaon', 0)
#             ))
            
#             db.commit()

#     print("🎉 Seeding Complete! 50 Products loaded.")
#     db.close()

# if __name__ == "__main__":
#     seed_database()