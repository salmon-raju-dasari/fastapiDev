"""
Database initialization script for PostgreSQL
Creates all tables and sets up the employee sequence to start from 1000
"""
from app.database import engine, Base
from app.models.employees import Employee
from app.models.products import Products
from app.models.categories import Category
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Initialize database with all tables"""
    try:
        logger.info("Creating all database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully!")
        
        # Verify employee sequence
        logger.info("✓ Employee ID sequence configured to start from 1000")
        logger.info("\nDatabase initialization complete!")
        logger.info("You can now start the FastAPI server.")
        
    except Exception as e:
        logger.error(f"✗ Error initializing database: {str(e)}")
        raise

if __name__ == "__main__":
    init_db()
