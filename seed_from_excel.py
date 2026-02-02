import pandas as pd
import os
import uuid
import re
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Product, ProductVariant, ProductImage, Category, Brand, CartItem, OrderItem, Review, Wishlist, Inventory, Location

# --- CONFIGURATION ---
FILE_PATH = "products.xlsx" 
SHEET_NAME = "Sheet2"
DEFAULT_PLACEHOLDER = "https://placehold.co/600?text=No+Image"
IMAGE_BASE_URL = "/assets/products/" 

def clean_price(price_val):
    if pd.isna(price_val): return 0.0
    # Handle Series (duplicate columns) by taking the first value
    if isinstance(price_val, pd.Series):
        price_val = price_val.iloc[0]
        
    clean = str(price_val).replace('$', '').replace(',', '').strip()
    try:
        return float(clean)
    except ValueError:
        return 0.0

def clean_text(val):
    # Handle Series (duplicate columns) by taking the first value
    if isinstance(val, pd.Series):
        val = val.iloc[0]
        
    if pd.isna(val) or str(val).strip() == "":
        return None
    return str(val).strip()

def find_best_column(df, candidates):
    """Returns the name of the first column found from the candidates list."""
    for candidate in candidates:
        for col in df.columns:
            if str(col).strip().lower() == candidate.lower():
                return col
    return None

def get_col_index(df, name_list):
    for i, col in enumerate(df.columns):
        if str(col).strip() in name_list:
            return i
    return None

def seed_data():
    db = SessionLocal()
    print(f"\n🚀 STARTING ROBUST IMPORT (Targeting {SHEET_NAME})...")
    
    # 1. WIPE DATABASE
    try:
        print("🗑️  Wiping database...")
        db.query(Inventory).delete()
        db.query(Review).delete()
        db.query(Wishlist).delete()
        db.query(OrderItem).delete()
        db.query(CartItem).delete()
        db.query(ProductImage).delete()
        db.query(ProductVariant).delete()
        db.query(Product).delete()
        db.query(Brand).delete()
        db.query(Category).delete()
        db.commit()
        print("✅ Database wiped.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error wiping DB: {e}")
        return

    # 2. SETUP CACHE & LOCATIONS
    print("🏭 Setting up Cache & Locations...")
    default_loc = db.query(Location).filter(Location.name == "Main Warehouse").first()
    if not default_loc:
        default_loc = Location(name="Main Warehouse")
        db.add(default_loc)
        db.commit()
        db.refresh(default_loc)
    warehouse_id = default_loc.id

    brand_cache = {}
    category_cache = {}

    # 3. READ DATA
    if not os.path.exists(FILE_PATH):
        print(f"❌ FATAL: Could not find '{FILE_PATH}'.")
        return

    try:
        df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
        
        # --- SMART COLUMN SELECTION ---
        # Instead of renaming duplicates, we find the SINGLE best column for each field.
        
        col_brand = find_best_column(df, ['BRAND', 'Mother Brand'])
        col_category = find_best_column(df, ['RANGE', 'Range', 'Category'])
        col_style = find_best_column(df, ['Style no', 'Style', 'Code'])
        col_name = find_best_column(df, ['Names', 'Name', 'Title'])
        col_desc = find_best_column(df, ['Description', 'Desc'])
        col_price = find_best_column(df, ['Price', 'Cost', 'MSRP'])
        col_image = find_best_column(df, ['Image1', 'Image URL', 'Image'])

        # Identify Variant Column Ranges
        idx_sizes = get_col_index(df, ['Sizes', 'Size'])
        idx_cups = get_col_index(df, ['Cups', 'Cup'])
        idx_colors = get_col_index(df, ['Colors', 'Color', 'Colour'])
        idx_price = get_col_index(df, ['Price', 'Cost'])

        if idx_sizes is None or idx_cups is None or idx_colors is None:
             print("❌ FATAL: Column mapping failed (Sizes/Cups/Colors missing).")
             return

        # 4. GROUPING LOGIC
        # Clean up the style column
        if col_style:
            df['clean_style'] = df[col_style].apply(lambda x: clean_text(x))
        else:
            df['clean_style'] = None

        # Generate Styles for rows that miss them
        for idx, row in df.iterrows():
            if not row['clean_style']:
                # Generate unique placeholder style
                name_part = str(row.get(col_name, 'GEN')).replace(' ', '')[:5].upper()
                df.at[idx, 'clean_style'] = f"{name_part}-{uuid.uuid4().hex[:4].upper()}"

        # Drop truly empty rows
        df = df.dropna(subset=['clean_style'])

        # Group by the unique Style Code
        grouped = df.groupby('clean_style')
        
        count_products = 0
        count_variants = 0

        print(f"   📍 Found {len(grouped)} unique styles. Processing...")

        for style_code, rows in grouped:
            try:
                # Use the first row to define the Product
                first_row = rows.iloc[0]
                
                brand_name = clean_text(first_row.get(col_brand, 'Generic')) or "Generic"
                category_name = clean_text(first_row.get(col_category, 'Lingerie')) or "Lingerie"
                product_name = clean_text(first_row.get(col_name))
                if not product_name: 
                    product_name = f"{brand_name} {style_code}"
                description = clean_text(first_row.get(col_desc)) or ""
                
                # 1. Brand
                if brand_name not in brand_cache:
                    b = Brand(name=brand_name)
                    db.add(b)
                    db.flush()
                    brand_cache[brand_name] = b.id
                brand_id = brand_cache[brand_name]

                # 2. Category
                if category_name not in category_cache:
                    c = Category(name=category_name)
                    db.add(c)
                    db.flush()
                    category_cache[category_name] = c.id
                category_id = category_cache[category_name]

                # 3. Create Product
                product_id = uuid.uuid4()
                product = Product(
                    id=product_id,
                    name=product_name,
                    description=description,
                    brand_id=brand_id,
                    category_id=category_id
                )
                db.add(product)
                count_products += 1

                # 4. Create Variants
                for _, row in rows.iterrows():
                    
                    # Extract Lists using indices
                    raw_sizes = row.iloc[idx_sizes : idx_cups].tolist()
                    valid_sizes = [str(x).strip() for x in raw_sizes if clean_text(x)]

                    raw_cups = row.iloc[idx_cups : idx_colors].tolist()
                    valid_cups = [str(x).strip() for x in raw_cups if clean_text(x)]

                    stop_idx = idx_price if idx_price and idx_price > idx_colors else len(df.columns)
                    raw_colors = row.iloc[idx_colors : stop_idx].tolist()
                    valid_colors = [str(x).strip() for x in raw_colors if clean_text(x)]
                    
                    price = clean_price(row.get(col_price))

                    if not valid_sizes: valid_sizes = ["One Size"]
                    if not valid_cups: valid_cups = [""]
                    if not valid_colors: valid_colors = ["Default"]

                    for size in valid_sizes:
                        for cup in valid_cups:
                            for color in valid_colors:
                                
                                display_size = f"{size} {cup}".strip()
                                safe_size_cup = f"{size}{cup}".replace(" ", "")
                                safe_color = color.replace(" ", "").upper()
                                variant_sku = f"{style_code}-{safe_color}-{safe_size_cup}".replace(" ", "-").upper()

                                variant_id = uuid.uuid4()
                                
                                var = ProductVariant(
                                    id=variant_id,
                                    product_id=product_id,
                                    color=color,
                                    size=display_size,
                                    price=price,
                                    sku=variant_sku
                                )
                                db.add(var)
                                count_variants += 1

                                # Inventory
                                inv = Inventory(
                                    variant_id=variant_id,
                                    location_id=warehouse_id,
                                    quantity=20
                                )
                                db.add(inv)

                                # Image
                                raw_img = clean_text(row.get(col_image))
                                final_img_url = DEFAULT_PLACEHOLDER
                                if raw_img:
                                    if raw_img.startswith('http'):
                                        final_img_url = raw_img
                                    else:
                                        final_img_url = f"{IMAGE_BASE_URL}{raw_img}"

                                img = ProductImage(
                                    variant_id=variant_id, 
                                    image_url=final_img_url, 
                                    alt_text=f"{product_name} - {color}"
                                )
                                db.add(img)

                db.commit()
                print(f"   ✅ Processed: {product_name}")

            except Exception as row_err:
                # If a group fails (e.g. duplicate SKU in same batch), log it but don't crash everything
                print(f"⚠️  Skipping Group {style_code}: {row_err}")
                db.rollback()

    except Exception as e:
        print(f"❌ Fatal Error: {e}")
    
    db.close()
    print(f"\n✨ DONE! Imported {count_products} Products and {count_variants} Variants.")

if __name__ == "__main__":
    seed_data()