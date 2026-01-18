"""
Migration script to format existing productid values as PRD{id}
Ensures all products have productid in the format PRD100, PRD101, etc.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL database configuration
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "supermarket")

# Create PostgreSQL database URL
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB]):
    raise ValueError("Database configuration not found in environment variables")

# Create engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def migrate_productid_format():
    """Update all products to have productid in PRD{id} format"""
    db = SessionLocal()
    try:
        print("Starting productid format migration...")
        
        # Update all products where productid is NULL or doesn't match PRD{id} format
        update_query = text("""
            UPDATE products 
            SET productid = CONCAT('PRD', id)
            WHERE productid IS NULL 
               OR productid = ''
               OR productid NOT LIKE 'PRD%'
        """)
        
        result = db.execute(update_query)
        db.commit()
        
        print(f"✅ Migration completed successfully!")
        print(f"   Updated {result.rowcount} product(s) with new productid format")
        
        # Show sample of updated products
        sample_query = text("""
            SELECT id, productid, productname 
            FROM products 
            ORDER BY id 
            LIMIT 10
        """)
        
        samples = db.execute(sample_query).fetchall()
        if samples:
            print("\n📋 Sample of products after migration:")
            for row in samples:
                print(f"   ID: {row.id} -> ProductID: {row.productid} -> Name: {row.productname}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("PRODUCTID FORMAT MIGRATION")
    print("=" * 60)
    print("This will update all products to have productid as PRD{id}")
    print()
    
    confirm = input("Do you want to proceed? (yes/no): ").strip().lower()
    if confirm == 'yes':
        migrate_productid_format()
        print("\n✅ All done!")
    else:
        print("Migration cancelled.")
