import os
from sqlalchemy import text
from database import engine

# Configuration
BASE_URL = "http://localhost:8000/static/products"
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "products")

def sync_images():
    print("📂 Scanning assets/products folder...")
    
    try:
        real_files = [f for f in os.listdir(ASSETS_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    except FileNotFoundError:
        print(f"❌ Error: Could not find folder: {ASSETS_DIR}")
        return

    print(f"✅ Found {len(real_files)} images on disk.")

    with engine.connect() as connection:
        print("🔄 performing smart match...")
        
        # Get all variants
        query = text("""
            SELECT v.id, p.name, v.color 
            FROM product_variants v 
            JOIN products p ON v.product_id = p.id
        """)
        variants = connection.execute(query).fetchall()

        updates = 0
        
        for v_id, p_name, v_color in variants:
            # Prepare tokens for matching
            # e.g., "Freya Fascinate Plunge Bra" -> ['freya', 'fascinate', 'plunge', 'bra']
            p_tokens = set(p_name.lower().split())
            
            # e.g., "Cherry" -> ['cherry']
            c_tokens = set(v_color.lower().split())

            best_match = None
            highest_score = 0

            for filename in real_files:
                f_lower = filename.lower()
                score = 0
                
                # Point for matching color (Critical)
                for token in c_tokens:
                    if token in f_lower:
                        score += 3 
                
                # Points for matching product name keywords
                for token in p_tokens:
                    if token in f_lower:
                        score += 1
                
                # Logic: We generally want at least the color AND one product word to match
                if score > highest_score:
                    highest_score = score
                    best_match = filename
            
            # Update DB if we found a decent match (score > 1 means at least color or 2 keywords matched)
            if best_match and highest_score > 1:
                full_url = f"{BASE_URL}/{best_match}"
                
                # Check if record exists
                check = connection.execute(text(f"SELECT id FROM product_images WHERE variant_id = '{v_id}'")).fetchone()
                
                if check:
                    connection.execute(text(f"UPDATE product_images SET image_url = '{full_url}' WHERE variant_id = '{v_id}'"))
                else:
                    # Insert if missing
                    esc_alt = f"{p_name} - {v_color}".replace("'", "")
                    connection.execute(text(f"INSERT INTO product_images (variant_id, image_url, alt_text, is_primary) VALUES ('{v_id}', '{full_url}', '{esc_alt}', true)"))
                
                print(f"✅ Matched: {p_name} ({v_color}) -> {best_match}")
                updates += 1
            else:
                print(f"⚠️ No match found for: {p_name} ({v_color})")

        connection.commit()
        print(f"🎉 Successfully updated {updates} product images!")

if __name__ == "__main__":
    sync_images()