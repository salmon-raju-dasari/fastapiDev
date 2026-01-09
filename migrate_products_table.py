"""
Database Migration Script for Products Table Update
This script updates the products table with new fields and structure

Run this script after updating the model to migrate existing data
"""

from sqlalchemy import create_engine, text
from app.database import SQLALCHEMY_DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_products_table():
    """
    Migrate the products table to the new schema
    """
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as connection:
        try:
            logger.info("Starting products table migration...")
            
            # Check if the old table exists
            result = connection.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'products'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info("Products table does not exist. It will be created with the new schema.")
                return
            
            # Backup the old table
            logger.info("Creating backup of existing products table...")
            connection.execute(text("""
                DROP TABLE IF EXISTS products_backup;
                CREATE TABLE products_backup AS SELECT * FROM products;
            """))
            connection.commit()
            logger.info("Backup created successfully")
            
            # Drop the old table
            logger.info("Dropping old products table...")
            connection.execute(text("DROP TABLE IF EXISTS products CASCADE;"))
            connection.commit()
            logger.info("Old table dropped")
            
            # Create new table with updated schema
            logger.info("Creating new products table with updated schema...")
            connection.execute(text("""
                CREATE TABLE products (
                    id SERIAL PRIMARY KEY,
                    
                    -- Product Identification (Required)
                    productid VARCHAR(100) UNIQUE NOT NULL,
                    productname VARCHAR(500) NOT NULL,
                    barcode VARCHAR(100) NOT NULL,
                    sku VARCHAR(100) UNIQUE,
                    
                    -- Product Details
                    description VARCHAR(2000),
                    brand VARCHAR(100),
                    category VARCHAR(100),
                    
                    -- Images (Array of max 5 images)
                    productimages TEXT[],
                    
                    -- Pricing & Units
                    price NUMERIC(10, 2) NOT NULL,
                    unitvalue BIGINT,
                    unit VARCHAR(50),
                    discount INTEGER DEFAULT 0,
                    gst INTEGER DEFAULT 0,
                    
                    -- Inventory
                    openingstock BIGINT DEFAULT 0,
                    quantity INTEGER DEFAULT 0,
                    
                    -- Dates
                    mfgdate VARCHAR(50),
                    expirydate VARCHAR(50),
                    
                    -- Supplier Information
                    suppliername VARCHAR(100),
                    suppliercontact VARCHAR(100),
                    
                    -- Custom Fields (JSON)
                    customfields JSONB,
                    
                    -- Metadata
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    updated_by VARCHAR(50)
                );
                
                -- Create indexes
                CREATE INDEX idx_products_productid ON products(productid);
                CREATE INDEX idx_products_barcode ON products(barcode);
                CREATE INDEX idx_products_sku ON products(sku);
                CREATE INDEX idx_products_category ON products(category);
                CREATE INDEX idx_products_brand ON products(brand);
            """))
            connection.commit()
            logger.info("New table created successfully with indexes")
            
            # Migrate data from backup (if there was data)
            logger.info("Checking for existing data to migrate...")
            result = connection.execute(text("SELECT COUNT(*) FROM products_backup"))
            count = result.scalar()
            
            if count > 0:
                logger.info(f"Migrating {count} existing products...")
                connection.execute(text("""
                    INSERT INTO products (
                        productid, productname, barcode, sku, description, 
                        brand, category, price, quantity, 
                        created_at, updated_at, updated_by
                    )
                    SELECT 
                        COALESCE(sku, 'PROD-' || id::text) as productid,
                        name as productname,
                        COALESCE(sku, 'BAR-' || id::text) as barcode,
                        sku,
                        description,
                        NULL as brand,
                        category,
                        price::numeric(10,2),
                        quantity,
                        created_at,
                        updated_at,
                        updated_by
                    FROM products_backup;
                """))
                connection.commit()
                logger.info(f"Successfully migrated {count} products")
            else:
                logger.info("No existing data to migrate")
            
            logger.info("Migration completed successfully!")
            logger.info("You can drop the backup table with: DROP TABLE products_backup;")
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            connection.rollback()
            raise


if __name__ == "__main__":
    try:
        migrate_products_table()
        print("\n✓ Migration completed successfully!")
        print("\nIMPORTANT: Please review the changes and test your application.")
        print("The backup table 'products_backup' has been created for safety.")
        print("You can drop it after verifying everything works correctly.")
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        print("\nPlease check the logs and fix any issues before running again.")
