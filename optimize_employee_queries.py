"""
Performance optimization script for employee queries
Adds indexes to speed up common query patterns
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

def optimize_employee_tables():
    """Add indexes to improve query performance"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            logger.info("Starting performance optimization...")
            
            # Index on employees table for filtering
            logger.info("Creating index on employees(business_id, role)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_employees_business_role 
                ON employees(business_id, role)
            """))
            
            logger.info("Creating index on employees(business_id, store_id)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_employees_business_store 
                ON employees(business_id, store_id)
            """))
            
            logger.info("Creating index on employees(email)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_employees_email 
                ON employees(email)
            """))
            
            # Index on employee_labels for faster custom field filtering
            logger.info("Creating index on employee_labels(emp_id, business_id)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_employee_labels_emp_business 
                ON employee_labels(emp_id, business_id)
            """))
            
            logger.info("Creating index on employee_labels(label_name, label_value)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_employee_labels_name_value 
                ON employee_labels(label_name, label_value)
            """))
            
            logger.info("Creating index on employee_labels(business_id, label_name)...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_employee_labels_business_name 
                ON employee_labels(business_id, label_name)
            """))
            
            # Analyze tables to update statistics
            logger.info("Analyzing tables to update query planner statistics...")
            conn.execute(text("ANALYZE employees"))
            conn.execute(text("ANALYZE employee_labels"))
            conn.execute(text("ANALYZE stores"))
            
            conn.commit()
            logger.info("✅ Performance optimization completed successfully!")
            
            # Show index information
            logger.info("\n=== Created Indexes ===")
            result = conn.execute(text("""
                SELECT 
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND tablename IN ('employees', 'employee_labels')
                ORDER BY tablename, indexname
            """))
            
            for row in result:
                logger.info(f"Table: {row[0]}, Index: {row[1]}")
            
        except Exception as e:
            logger.error(f"Error during optimization: {str(e)}")
            conn.rollback()
            raise

if __name__ == "__main__":
    optimize_employee_tables()
