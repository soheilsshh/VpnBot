from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey, TIMESTAMP, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

from datetime import datetime
from config import DATABASE_URL

#declear base for using sqlAlchemy
Base = declarative_base()

#   User model
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    wallet_balance = Column(Float, default=0)
    is_admin = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

#  Services model
class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)  
    price = Column(Float, nullable=False)   
    duration = Column(Integer, nullable=False) 
    data_limit = Column(Integer) 
    is_active = Column(Boolean, default=True) 
    inbound_id = Column(Integer)    
    
    
class UserService(Base):
    __tablename__ = 'user_services'
     
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False) 
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False) 
    marzban_username = Column(String) 
    expire_date = Column(TIMESTAMP)  
    data_limit = Column(Integer)  
    data_used = Column(Integer, default=0) 
    is_active = Column(Boolean, default=True)  
    created_at = Column(TIMESTAMP, default=datetime.utcnow)  

    user = relationship("User", back_populates="user_services")  
    service = relationship("Service")  
    

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True) 
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False) 
    amount = Column(Float, nullable=False) 
    type = Column(String)  
    status = Column(String)  
    created_at = Column(TIMESTAMP, default=datetime.utcnow)  
    user = relationship("User", back_populates="transactions")

class DiscountCode(Base):
    __tablename__ = 'discount_codes'

    id = Column(Integer, primary_key=True, autoincrement=True) 
    code = Column(String, unique=True, nullable=False)  
    type = Column(String)  
    amount = Column(Float)  
    is_active = Column(Boolean, default=True)  
    used_count = Column(Integer, default=0)  
    created_at = Column(TIMESTAMP, default=datetime.utcnow)  

class SystemLog(Base):
    __tablename__ = 'system_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)  
    level = Column(String)  
    module = Column(String) 
    message = Column(String) 
    details = Column(String) 
    created_at = Column(TIMESTAMP, default=datetime.utcnow) 

class ErrorLog(Base):
    __tablename__ = 'error_logs'

    id = Column(Integer, primary_key=True, autoincrement=True) 
    error_type = Column(String) 
    error_message = Column(String) 
    traceback = Column(String)
    user_id = Column(Integer, ForeignKey('users.id')) 
    created_at = Column(TIMESTAMP, default=datetime.utcnow)  

class Report(Base):
    __tablename__ = 'reports'

    id = Column(Integer, primary_key=True, autoincrement=True) 
    type = Column(String) 
    start_date = Column(TIMESTAMP) 
    end_date = Column(TIMESTAMP)  
    total_sales = Column(Float)  
    total_transactions = Column(Integer)  
    new_users = Column(Integer)  
    active_services = Column(Integer) 
    data = Column(String)  
    created_at = Column(TIMESTAMP, default=datetime.utcnow)  

class Backup(Base):
    __tablename__ = 'backups'

    id = Column(Integer, primary_key=True, autoincrement=True)  
    filename = Column(String)  
    size = Column(Integer)  
    type = Column(String)  
    status = Column(String)  
    note = Column(String)  
    created_at = Column(TIMESTAMP, default=datetime.utcnow)  

   
class Database:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine) 
        self.Session = sessionmaker(bind=self.engine)
        
            
    def create_user(self, telegram_id, username=None, is_admin=False):
        session = self.Session()
        try:
            new_user = User(telegram_id=telegram_id, username=username, is_admin=is_admin)
            session.add(new_user)
            session.commit()
            return new_user.id  
        except Exception as e:
            session.rollback()  
            print(f"Error occurred: {e}")
            return None
        finally:
            session.close()
            
    
    def get_user(self, telegram_id):
        session = self.Session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).one()  
            return user  
        except FileNotFoundError:
            print("User not found.")
            return None
        finally:
            session.close() 
            
#             conn.commit()
    
#     # User methods
#     def create_user(self, telegram_id, username=None, is_admin=False):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'INSERT OR IGNORE INTO users (telegram_id, username, is_admin) VALUES (?, ?, ?)',
#                 (telegram_id, username, is_admin)
#             )
#             conn.commit()
#             return cursor.lastrowid
    
#     def get_user(self, telegram_id):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
#             return cursor.fetchone()
    
#     def update_user_balance(self, telegram_id, amount):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'UPDATE users SET wallet_balance = wallet_balance + ? WHERE telegram_id = ?',
#                 (amount, telegram_id)
#             )
#             conn.commit()
    
#     # Service methods
#     def create_service(self, name, price, duration, data_limit, inbound_id=1):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'INSERT INTO services (name, price, duration, data_limit, inbound_id) VALUES (?, ?, ?, ?, ?)',
#                 (name, price, duration, data_limit, inbound_id)
#             )
#             conn.commit()
#             return cursor.lastrowid
    
#     def get_active_services(self):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute('SELECT * FROM services WHERE is_active = 1')
#             return cursor.fetchall()
    
#     def get_service(self, service_id):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
#             return cursor.fetchone()
    
#     # User service methods
#     def create_user_service(self, user_id, service_id, marzban_username, expire_date, data_limit):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 '''INSERT INTO user_services 
#                    (user_id, service_id, marzban_username, expire_date, data_limit)
#                    VALUES (?, ?, ?, ?, ?)''',
#                 (user_id, service_id, marzban_username, expire_date, data_limit)
#             )
#             conn.commit()
#             return cursor.lastrowid
    
#     def get_user_active_services(self, user_id: int):
#         """Get user's active services with service details"""
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute('''
#                 SELECT 
#                     us.id,
#                     us.user_id,
#                     us.service_id,
#                     us.marzban_username,
#                     us.expire_date,
#                     us.data_limit,
#                     COALESCE(us.data_used, 0) as data_used,
#                     us.is_active,
#                     s.name,
#                     s.price 
#                 FROM user_services us 
#                 JOIN services s ON us.service_id = s.id 
#                 WHERE us.user_id = ? AND us.is_active = 1
#             ''', (user_id,))
#             return cursor.fetchall()
    
#     # Transaction methods
#     def create_transaction(self, user_id, amount, type_, status='pending'):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'INSERT INTO transactions (user_id, amount, type, status) VALUES (?, ?, ?, ?)',
#                 (user_id, amount, type_, status)
#             )
#             conn.commit()
#             return cursor.lastrowid
    
#     def update_transaction_status(self, transaction_id, status):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'UPDATE transactions SET status = ? WHERE id = ?',
#                 (status, transaction_id)
#             )
#             conn.commit()
    
#     # Discount code methods
#     def create_discount_code(self, code, type_, amount):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'INSERT INTO discount_codes (code, type, amount) VALUES (?, ?, ?)',
#                 (code.upper(), type_, amount)
#             )
#             conn.commit()
#             return cursor.lastrowid
    
#     def get_discount_code(self, code):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'SELECT * FROM discount_codes WHERE code = ? AND is_active = 1',
#                 (code.upper(),)
#             )
#             return cursor.fetchone()
    
#     def use_discount_code(self, code):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'UPDATE discount_codes SET used_count = used_count + 1 WHERE code = ?',
#                 (code.upper(),)
#             )
#             conn.commit()
    
#     # Logging methods
#     def log_system(self, level, module, message, details=None):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'INSERT INTO system_logs (level, module, message, details) VALUES (?, ?, ?, ?)',
#                 (level, module, message, json.dumps(details) if details else None)
#             )
#             conn.commit()
    
#     def log_error(self, error_type, error_message, traceback, user_id=None):
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 'INSERT INTO error_logs (error_type, error_message, traceback, user_id) VALUES (?, ?, ?, ?)',
#                 (error_type, error_message, traceback, user_id)
#             )
#             conn.commit()

#     def get_user_by_id(self, user_id: int):
#         """Get user by database ID"""
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
#             return cursor.fetchone()

#     def get_service_by_id(self, service_id: int):
#         """Get service by ID"""
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
#             return cursor.fetchone()

#     def create_user_service(self, user_id: int, service_id: int, marzban_username: str, expire_date: str, data_limit: int):
#         """Create new user service"""
#         with self.get_connection() as conn:
#             cursor = conn.cursor()
#             cursor.execute(
#                 '''INSERT INTO user_services 
#                    (user_id, service_id, marzban_username, expire_date, data_limit)
#                    VALUES (?, ?, ?, ?, ?)''',
#                 (user_id, service_id, marzban_username, expire_date, data_limit)
#             )
#             conn.commit()
#             return cursor.lastrowid 
