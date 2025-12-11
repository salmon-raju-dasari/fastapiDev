"""
Migration script to add store_sequence column to stores table
Assigns sequence numbers to existing stores per business
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import SQLALCHEMY_DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_store_sequence_column():
    """Add store_sequence column and populate it for existing stores"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='stores' AND column_name='store_sequence'
        """))
        
        if result.fetchone():
            logger.info("Column 'store_sequence' already exists in stores table")
            return
        
        logger.info("Adding store_sequence column to stores table...")
        
        # Add the column (allow NULL initially)
        db.execute(text("""
            ALTER TABLE stores 
            ADD COLUMN store_sequence INTEGER
        """))
        db.commit()
        logger.info("Column added successfully")
        
        # Get all businesses and their stores
        logger.info("Assigning sequence numbers to existing stores...")
        businesses = db.execute(text("""
            SELECT DISTINCT business_id FROM stores ORDER BY business_id
        """)).fetchall()
        
        for business_row in businesses:
            business_id = business_row[0]
            logger.info(f"Processing stores for business: {business_id}")
            
            # Get all stores for this business, ordered by creation date
            stores = db.execute(text("""
                SELECT id FROM stores 
                WHERE business_id = :business_id 
                ORDER BY created_at, id
            """), {"business_id": business_id}).fetchall()
            
            # Assign sequence numbers
            for idx, store_row in enumerate(stores, start=1):
                store_id = store_row[0]
                db.execute(text("""
                    UPDATE stores 
                    SET store_sequence = :sequence 
                    WHERE id = :store_id
                """), {"sequence": idx, "store_id": store_id})
                logger.info(f"  Store ID {store_id} -> Sequence {idx}")
            
            db.commit()
        
        # Make the column NOT NULL now that all values are set
        logger.info("Making store_sequence column NOT NULL...")
        db.execute(text("""
            ALTER TABLE stores 
            ALTER COLUMN store_sequence SET NOT NULL
        """))
        db.commit()
        
        logger.info("Migration completed successfully!")
        logger.info("Store sequences have been assigned to all existing stores")
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting store_sequence migration...")
    add_store_sequence_column()
    logger.info("Migration script finished")
