"""
Migration script to make business_id the primary key in business table
Removes id column and sets business_id as primary key for better performance
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

def migrate_business_table():
    """Make business_id the primary key"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            logger.info("Starting business table migration...")
            
            # Check if business table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'business'
                );
            """))
            if not result.scalar():
                logger.error("Business table does not exist!")
                return
            
            # Check current structure
            logger.info("Current business table structure:")
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'business'
                ORDER BY ordinal_position;
            """))
            for row in result:
                logger.info(f"  {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")
            
            # Step 1: Drop existing primary key constraint on id column
            logger.info("Step 1: Dropping existing primary key constraint...")
            conn.execute(text("""
                ALTER TABLE business DROP CONSTRAINT IF EXISTS business_pkey;
            """))
            
            # Step 2: Drop foreign key constraints from stores table
            logger.info("Step 2: Dropping foreign key constraint from stores table...")
            conn.execute(text("""
                ALTER TABLE stores DROP CONSTRAINT IF EXISTS stores_business_id_fkey;
            """))
            
            # Step 3: Drop unique constraint on business_id if exists
            logger.info("Step 3: Dropping unique constraint on business_id...")
            conn.execute(text("""
                ALTER TABLE business DROP CONSTRAINT IF EXISTS business_business_id_key;
            """))
            
            # Step 4: Drop index on business_id if exists (since it will be recreated as PK)
            logger.info("Step 4: Dropping index on business_id...")
            conn.execute(text("""
                DROP INDEX IF EXISTS ix_business_business_id CASCADE;
            """))
            
            # Step 5: Make business_id the primary key
            logger.info("Step 5: Setting business_id as primary key...")
            conn.execute(text("""
                ALTER TABLE business ADD PRIMARY KEY (business_id);
            """))
            
            # Step 6: Recreate foreign key constraint from stores to business
            logger.info("Step 6: Recreating foreign key constraint from stores table...")
            conn.execute(text("""
                ALTER TABLE stores 
                ADD CONSTRAINT stores_business_id_fkey 
                FOREIGN KEY (business_id) REFERENCES business(business_id) 
                ON DELETE CASCADE;
            """))
            
            # Step 7: Drop the old id column
            logger.info("Step 7: Dropping id column...")
            conn.execute(text("""
                ALTER TABLE business DROP COLUMN IF EXISTS id;
            """))
            
            # Commit transaction
            conn.commit()
            logger.info("✅ Business table migration completed successfully!")
            
            # Show new structure
            logger.info("\nNew business table structure:")
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'business'
                ORDER BY ordinal_position;
            """))
            for row in result:
                logger.info(f"  {row[0]}: {row[1]} (nullable: {row[2]})")
            
            # Show primary key
            logger.info("\nPrimary key:")
            result = conn.execute(text("""
                SELECT constraint_name, column_name
                FROM information_schema.key_column_usage
                WHERE table_name = 'business' 
                AND constraint_name LIKE '%pkey%';
            """))
            for row in result:
                logger.info(f"  {row[0]}: {row[1]}")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error during migration: {str(e)}")
            raise

if __name__ == "__main__":
    migrate_business_table()
