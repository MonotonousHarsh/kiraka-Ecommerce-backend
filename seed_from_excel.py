import pandas as pd
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Product, ProductVariant, Inventory, Location

# Configuration
EXCEL_FILE = "products.xlsx"
SHEET_NAME = "Sheet1" # The Inventory Sheet

def find_header_row(df):
    """Finds the row containing 'Retail Price' and 'Style No'."""
    for index, row in df.iterrows():
        row_str = str(row.values).lower()
        if "retail price" in row_str and "style no" in row_str:
            return index
    return 0

def sync_stock():
    db = SessionLocal()
    print(f"📊 Reading Inventory from '{SHEET_NAME}'...")
    
    try:
        # 1. Setup Location (Warehouse)
        warehouse = db.query(Location).filter_by(name="Main Warehouse").first()
        if not warehouse:
            warehouse = Location(name="Main Warehouse")
            db.add(warehouse)
            db.commit()

        # 2. Read Excel
        raw_df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, header=None)
        start_row = find_header_row(raw_df)
        print(f"🔍 Detected Inventory Headers at Index: {start_row}")
        
        df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME, header=start_row)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Map columns
        col_map = {
            "style": None, "price": None, "qty": None, 
            "size": None, "cup": None, "color": None
        }
        
        for col in df.columns:
            if "style" in col: col_map["style"] = col
            if "retail" in col or "price" in col: col_map["price"] = col
            if "qty" in col or "quantity" in col: col_map["qty"] = col
            if "size" in col: col_map["size"] = col
            if "cup" in col: col_map["cup"] = col
            # Prefer 'color name', fallback to 'color code' or just 'color'
            if "color" in col and "name" in col: col_map["color"] = col
            elif "color" in col and col_map["color"] is None: col_map["color"] = col

        if not col_map["style"] or not col_map["price"]:
            print("❌ Error: Could not find Style No or Price columns.")
            return

        print(f"✅ mapped Columns: {col_map}")

        # 3. Loop Rows
        updated_count = 0
        variants_added = 0
        
        for index, row in df.iterrows():
            style_no = str(row.get(col_map["style"])).strip()
            if not style_no or style_no.lower() == 'nan': continue

            # --- SEARCH FOR PARENT PRODUCT ---
            # We look for a product whose name contains this style number
            # e.g. "Matilda - EL8900" contains "EL8900"
            product = db.query(Product).filter(Product.name.ilike(f"%{style_no}%")).first()
            
            if not product:
                # OPTION B: Skip if product doesn't exist
                continue

            # --- GET VARIANT DETAILS ---
            color = str(row.get(col_map["color"], "Standard")).strip()
            size = str(row.get(col_map["size"], "")).strip()
            cup = str(row.get(col_map["cup"], "")).strip()
            if cup == 'nan': cup = ""
            
            # Combine Size + Cup (e.g. "34" + "B" = "34B")
            full_size = f"{size}{cup}"
            if not full_size: continue

            # Generate SKU
            sku = f"{style_no}-{color}-{full_size}".upper().replace(" ", "")

            price = row.get(col_map["price"], 0)
            try: price = float(price)
            except: price = 0.0

            qty = row.get(col_map["qty"], 0)
            try: qty = int(qty)
            except: qty = 0

            # --- UPDATE OR CREATE VARIANT ---
            variant = db.query(ProductVariant).filter_by(sku=sku).first()
            
            if not variant:
                # Create new variant (e.g. we had 34B, now we found 34C in sheet)
                variant = ProductVariant(
                    product_id=product.id,
                    sku=sku,
                    color=color,
                    size=full_size,
                    price=price
                )
                db.add(variant)
                db.commit()
                db.refresh(variant)
                variants_added += 1
            else:
                # Update existing price
                variant.price = price
                # Ensure correct color/size labeling if it was messy before
                variant.color = color 
                variant.size = full_size
            
            # --- UPDATE INVENTORY ---
            inventory = db.query(Inventory).filter_by(variant_id=variant.id).first()
            if not inventory:
                inventory = Inventory(
                    variant_id=variant.id,
                    location_id=warehouse.id,
                    quantity=qty
                )
                db.add(inventory)
            else:
                inventory.quantity = qty
            
            updated_count += 1
            if updated_count % 50 == 0:
                db.commit()
                print(f"   ... Processed {updated_count} variants")

        db.commit()
        print(f"🎉 Success! Synced {updated_count} stock entries.")
        print(f"   (Added {variants_added} new size/color options to existing products)")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    sync_stock()