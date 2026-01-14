"""
Migration script to add business_id column to products table
This ensures each product belongs to a specific business
"""
import logging
from sqlalchemy import create_engine, text
import os
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_business_id_to_products():
    """Add business_id column to products table"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            logger.info("Starting products table migration...")
            
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='products' AND column_name='business_id';
            """))
            
            if result.fetchone():
                logger.info("business_id column already exists in products table")
                return
            
            # Step 1: Add business_id column (nullable initially)
            logger.info("Step 1: Adding business_id column...")
            conn.execute(text("""
                ALTER TABLE products 
                ADD COLUMN business_id VARCHAR(50);
            """))
            
            # Step 2: Set a default business_id for existing products (use first business)
            logger.info("Step 2: Setting default business_id for existing products...")
            result = conn.execute(text("""
                SELECT business_id FROM business LIMIT 1;
            """))
            default_business = result.fetchone()
            
            if default_business:
                logger.info(f"Setting existing products to business_id: {default_business[0]}")
                conn.execute(text("""
                    UPDATE products 
                    SET business_id = :business_id 
                    WHERE business_id IS NULL;
                """), {"business_id": default_business[0]})
            else:
                logger.warning("No business found! Creating a default business entry...")
                conn.execute(text("""
                    INSERT INTO business (business_id, business_name, owner_name, phone_number, email)
                    VALUES ('1', 'Default Business', 'Admin', '0000000000', 'admin@example.com')
                    ON CONFLICT DO NOTHING;
                """))
                conn.execute(text("""
                    UPDATE products 
                    SET business_id = '1' 
                    WHERE business_id IS NULL;
                """))
            
            # Step 3: Make business_id NOT NULL
            logger.info("Step 3: Making business_id NOT NULL...")
            conn.execute(text("""
                ALTER TABLE products 
                ALTER COLUMN business_id SET NOT NULL;
            """))
            
            # Step 4: Add foreign key constraint
            logger.info("Step 4: Adding foreign key constraint...")
            conn.execute(text("""
                ALTER TABLE products 
                ADD CONSTRAINT products_business_id_fkey 
                FOREIGN KEY (business_id) REFERENCES business(business_id) 
                ON DELETE CASCADE;
            """))
            
            # Step 5: Add index for better query performance
            logger.info("Step 5: Adding index on business_id...")
            conn.execute(text("""
                CREATE INDEX idx_products_business_id ON products(business_id);
            """))
            
            conn.commit()
            logger.info("✅ Products table migration completed successfully!")
            
            # Show updated structure
            logger.info("\nUpdated products table structure:")
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'products' AND column_name = 'business_id';
            """))
            for row in result:
                logger.info(f"  {row[0]}: {row[1]} (nullable: {row[2]})")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during migration: {str(e)}")
            raise

if __name__ == "__main__":
    add_business_id_to_products()
