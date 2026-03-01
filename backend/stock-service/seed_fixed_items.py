import uuid
import logging
# Import all models to ensure relationships resolve
import app.models.transaction
from app.core.database import SessionLocal
from app.models.inventory import Item, Inventory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ITEMS = [
    {"id": "550e8400-e29b-41d4-a716-446655440001", "name": "Burger", "price": 5.99, "qty": 100},
    {"id": "550e8400-e29b-41d4-a716-446655440002", "name": "Pizza", "price": 8.99, "qty": 100},
    {"id": "550e8400-e29b-41d4-a716-446655440003", "name": "Salad", "price": 4.99, "qty": 100},
    {"id": "550e8400-e29b-41d4-a716-446655440004", "name": "Fries", "price": 2.99, "qty": 100},
    {"id": "550e8400-e29b-41d4-a716-446655440005", "name": "Soda", "price": 1.99, "qty": 100},
]

def seed():
    db = SessionLocal()
    try:
        for data in ITEMS:
            item_id = uuid.UUID(data["id"])
            item = db.query(Item).filter(Item.id == item_id).first()
            
            if not item:
                logger.info(f"Creating item: {data['name']} ({data['id']})")
                item = Item(id=item_id, name=data["name"], price=data["price"])
                db.add(item)
                db.commit()
                
                # Add inventory
                inventory = Inventory(item_id=item_id, quantity=data["qty"])
                db.add(inventory)
                db.commit()
            else:
                logger.info(f"Item exists: {data['name']} ({data['id']})")
                
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
