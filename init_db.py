from database import Base, User, Service, UserService, Transaction, DiscountCode, SystemLog, ErrorLog, Report, Backup
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config import DATABASE_URL, ADMIN_ID, SERVICE_TEMPLATES

def init_database():
    """Initialize database and create default data"""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    
    print("✅ Database tables created successfully!")
    
    # Create admin user
    try:
        with Session(engine) as session:
            admin = User(
                telegram_id=ADMIN_ID,
                username="admin",
                is_admin=True
            )
            session.add(admin)
            session.commit()
            print("✅ Admin user created successfully!")
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
    
    # Create default services
    try:
        with Session(engine) as session:
            for template in SERVICE_TEMPLATES.values():
                service = Service(**template)
                session.add(service)
            session.commit()
            print("✅ Default services created successfully!")
    except Exception as e:
        print(f"❌ Error creating default services: {e}")

if __name__ == "__main__":
    print("Initializing database...")
    init_database()
    print("Done!") 