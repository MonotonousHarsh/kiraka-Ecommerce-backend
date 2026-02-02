from sqlalchemy import text
from database import engine

def check_images():
    print(f"{'PRODUCT':<30} | {'COLOR':<15} | {'ASSIGNED IMAGE'}")
    print("-" * 80)
    
    with engine.connect() as connection:
        query = text("""
            SELECT p.name, v.color, i.image_url 
            FROM product_variants v 
            JOIN products p ON v.product_id = p.id
            LEFT JOIN product_images i ON i.variant_id = v.id
        """)
        results = connection.execute(query).fetchall()
        
        for name, color, url in results:
            filename = url.split('/')[-1] if url else "NO IMAGE"
            print(f"{name[:28]:<30} | {color[:13]:<15} | {filename}")

if __name__ == "__main__":
    check_images()