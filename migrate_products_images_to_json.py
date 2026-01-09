"""
Migration script to convert productimages from ARRAY(String) to JSON
This allows storing base64 image data instead of URLs
"""
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL database configuration (same as database.py)
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "supermarket_db")

# Create PostgreSQL database URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def migrate_productimages_column():
    """Convert productimages column from ARRAY to JSON"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("PRODUCT IMAGES COLUMN MIGRATION")
        print("=" * 80)
        
        # Check current column type
        inspector = inspect(engine)
        columns = inspector.get_columns('products')
        productimages_col = next((col for col in columns if col['name'] == 'productimages'), None)
        
        if not productimages_col:
            print("❌ ERROR: productimages column not found")
            return False
            
        print(f"\nCurrent column type: {productimages_col['type']}")
        
        # Check if migration is needed
        if 'JSON' in str(productimages_col['type']):
            print("✅ Column is already JSON type. No migration needed.")
            return True
        
        print("\n🔄 Starting migration...")
        
        # Step 1: Create backup of data
        print("\n1️⃣ Creating backup of existing data...")
        result = db.execute(text("SELECT COUNT(*) FROM products WHERE productimages IS NOT NULL"))
        count = result.scalar()
        print(f"   Found {count} products with images")
        
        # Step 2: Convert ARRAY data to JSON format
        print("\n2️⃣ Converting existing data...")
        # First, create a temporary column
        db.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS productimages_temp JSON"))
        db.commit()
        
        # Copy and convert data from array to JSON
        db.execute(text("""
            UPDATE products 
            SET productimages_temp = to_jsonb(productimages)
            WHERE productimages IS NOT NULL
        """))
        db.commit()
        print("   ✅ Data converted to JSON format")
        
        # Step 3: Drop old column and rename new one
        print("\n3️⃣ Replacing old column with new JSON column...")
        db.execute(text("ALTER TABLE products DROP COLUMN productimages"))
        db.execute(text("ALTER TABLE products RENAME COLUMN productimages_temp TO productimages"))
        db.commit()
        print("   ✅ Column type changed successfully")
        
        # Step 4: Verify migration
        print("\n4️⃣ Verifying migration...")
        inspector = inspect(engine)
        columns = inspector.get_columns('products')
        productimages_col = next((col for col in columns if col['name'] == 'productimages'), None)
        print(f"   New column type: {productimages_col['type']}")
        
        result = db.execute(text("SELECT COUNT(*) FROM products WHERE productimages IS NOT NULL"))
        new_count = result.scalar()
        print(f"   Products with images after migration: {new_count}")
        
        if new_count == count:
            print("   ✅ Data integrity verified")
        else:
            print(f"   ⚠️  WARNING: Data count mismatch (before: {count}, after: {new_count})")
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nNOTE: Product images are now stored as JSON arrays")
        print("Frontend should send base64 encoded images in the productimages array")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: Migration failed - {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("\n⚠️  WARNING: This will modify the products table structure")
    print("   - productimages column will be changed from ARRAY to JSON")
    print("   - Existing image URLs will be preserved as JSON array")
    
    response = input("\nDo you want to proceed? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        success = migrate_productimages_column()
        sys.exit(0 if success else 1)
    else:
        print("\n❌ Migration cancelled by user")
        sys.exit(0)
