"""
Drop and recreate the entire database with fresh schema
WARNING: This will delete ALL data!
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging
from app.database import Base, engine
from app.models import business, employees, stores, categories, products, payment, custom_labels, employee_labels

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_and_create_database():
    """Drop the existing database and create a fresh one"""
    
    # Database connection parameters
    DB_HOST = "localhost"
    DB_PORT = "5432"
    DB_USER = "postgres"
    DB_PASSWORD = "admin"
    DB_NAME = "supermarket_db"
    
    try:
        # Connect to PostgreSQL server (not to specific database)
        logger.info("Connecting to PostgreSQL server...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres"  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Terminate existing connections to the database
        logger.info(f"Terminating existing connections to '{DB_NAME}'...")
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{DB_NAME}'
            AND pid <> pg_backend_pid();
        """)
        
        # Drop the database
        logger.info(f"Dropping database '{DB_NAME}'...")
        cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
        logger.info(f"✓ Database '{DB_NAME}' dropped successfully")
        
        # Create fresh database
        logger.info(f"Creating fresh database '{DB_NAME}'...")
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        logger.info(f"✓ Database '{DB_NAME}' created successfully")
        
        cursor.close()
        conn.close()
        
        # Create all tables using SQLAlchemy
        logger.info("Creating all tables with SQLAlchemy...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ All tables created successfully")
        
        logger.info("\n" + "="*60)
        logger.info("✓ Database recreation completed successfully!")
        logger.info("="*60)
        logger.info("You can now start fresh with a clean database.")
        
    except Exception as e:
        logger.error(f"Error during database recreation: {e}")
        raise

if __name__ == "__main__":
    response = input("⚠️  WARNING: This will DELETE ALL DATA! Are you sure? (yes/no): ")
    if response.lower() == "yes":
        drop_and_create_database()
    else:
        logger.info("Operation cancelled.")
