from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Item, Inventory
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
# Using localhost:5433 to connect to Docker Postgres from host
DB_URL = "postgresql://cafeteria:cafeteria_pass@localhost:5433/cafeteria_db"

def init_db():
    engine = create_engine(DB_URL)
    
    logger.info("Creating tables...")
    Base.metadata.create_all(engine)
    logger.info("Tables created successfully.")

    Session = sessionmaker(bind=engine)
    session = Session()

    # Check if we have items, if not add some sample data
    if session.query(Item).count() == 0:
        logger.info("Adding sample data...")
        
        # Create Items
        item1 = Item(name="Burger", price=5.99)
        item2 = Item(name="Fries", price=2.99)
        item3 = Item(name="Coke", price=1.99)
        
        session.add_all([item1, item2, item3])
        session.commit() # Commit to get IDs
        
        # Create Inventory
        inv1 = Inventory(item_id=item1.id, quantity=100)
        inv2 = Inventory(item_id=item2.id, quantity=200)
        inv3 = Inventory(item_id=item3.id, quantity=300)
        
        session.add_all([inv1, inv2, inv3])
        session.commit()
        
        logger.info("Sample data added.")
    else:
        logger.info("Data already exists.")

    session.close()

if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
