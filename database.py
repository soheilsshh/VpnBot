from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey, TIMESTAMP, Text, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json

# Declare base for using SQLAlchemy
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    wallet_balance = Column(Float, default=0)
    is_admin = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    user_services = relationship("UserService", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")


# Service model
class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    duration = Column(Integer, nullable=False)
    data_limit = Column(Integer)
    is_active = Column(Boolean, default=True)
    inbound_id = Column(Integer)


# UserService model
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


# Transaction model
class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String)
    status = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")


# DiscountCode model
class DiscountCode(Base):
    __tablename__ = 'discount_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    type = Column(String)
    amount = Column(Float)
    is_active = Column(Boolean, default=True)
    used_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


# SystemLog model
class SystemLog(Base):
    __tablename__ = 'system_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String)
    module = Column(String)
    message = Column(String)
    details = Column(String)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


# ErrorLog model
class ErrorLog(Base):
    __tablename__ = 'error_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    error_type = Column(String)
    error_message = Column(String)
    traceback = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class Backup(Base):
    __tablename__ = 'backups'

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    note = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Database:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    # User methods
    def create_user(self, telegram_id, username=None, is_admin=False):
        session = self.Session()
        try:
            new_user = User(telegram_id=telegram_id, username=username, is_admin=is_admin)
            session.add(new_user)
            session.commit()
            return new_user.id
        except Exception as e:
            session.rollback()
            print(f"Error creating user: {e}")
            return None
        finally:
            session.close()

    def get_user(self, telegram_id):
        session = self.Session()
        try:
            return session.query(User).filter_by(telegram_id=telegram_id).first()
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
        finally:
            session.close()

    def update_user_balance(self, telegram_id, amount):
        session = self.Session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                new_balance = user.wallet_balance + amount

                # Debugging
                print(f"Current Balance: {user.wallet_balance}, Amount: {amount}, New Balance: {new_balance}")

                # Optional: Prevent negative balances if necessary
                if new_balance < 0:
                    print("Insufficient balance!")
                    return False

                user.wallet_balance = new_balance
                session.commit()
                return True
            else:
                print("User not found.")
                return False
        except Exception as e:
            session.rollback()
            print(f"Error updating user balance: {e}")
            return False
        finally:
            session.close()


    # Service methods
    def create_service(self, name, price, duration, data_limit, inbound_id=1):
        session = self.Session()
        try:
            new_service = Service(
                name=name,
                price=price,
                duration=duration,
                data_limit=data_limit,
                inbound_id=inbound_id
            )
            session.add(new_service)
            session.commit()
            return new_service.id
        except Exception as e:
            session.rollback()
            print(f"Error creating service: {e}")
            return None
        finally:
            session.close()

    def get_active_services(self):
        session = self.Session()
        try:
            return session.query(Service).filter_by(is_active=True).all()
        except Exception as e:
            print(f"Error getting active services: {e}")
            return []
        finally:
            session.close()

    def get_service(self, service_id):
        session = self.Session()
        try:
            return session.query(Service).get(service_id)
        except Exception as e:
            print(f"Error getting service: {e}")
            return None
        finally:
            session.close()

    # UserService methods
    def create_user_service(self, user_id, service_id, marzban_username, expire_date, data_limit):
        session = self.Session()
        try:
            new_user_service = UserService(
                user_id=user_id,
                service_id=service_id,
                marzban_username=marzban_username,
                expire_date=expire_date,
                data_limit=data_limit
            )
            session.add(new_user_service)
            session.commit()
            return new_user_service.id
        except Exception as e:
            session.rollback()
            print(f"Error creating user service: {e}")
            return None
        finally:
            session.close()

    def get_user_active_services(self, user_id: int):
        session = self.Session()
        try:
            return session.query(
                UserService.id,
                UserService.user_id,
                UserService.service_id,
                UserService.marzban_username,
                UserService.expire_date,
                UserService.data_limit,
                func.coalesce(UserService.data_used, 0).label('data_used'),
                UserService.is_active,
                Service.name,
                Service.price
            ).join(Service).filter(
                UserService.user_id == user_id,
                UserService.is_active == True
            ).all()
        except Exception as e:
            print(f"Error getting user active services: {e}")
            return []
        finally:
            session.close()

    # Transaction methods
    def create_transaction(self, user_id, amount, type_, status='pending'):
        session = self.Session()
        try:
            new_transaction = Transaction(
                user_id=user_id,
                amount=amount,
                type=type_,
                status=status
            )
            session.add(new_transaction)
            session.commit()
            return new_transaction.id
        except Exception as e:
            session.rollback()
            print(f"Error creating transaction: {e}")
            return None
        finally:
            session.close()

    def update_transaction_status(self, transaction_id, status):
        session = self.Session()
        try:
            transaction = session.query(Transaction).get(transaction_id)
            if transaction:
                transaction.status = status
                session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error updating transaction status: {e}")
        finally:
            session.close()

    # DiscountCode methods
    def create_discount_code(self, code, type_, amount):
        session = self.Session()
        try:
            new_code = DiscountCode(
                code=code.upper(),
                type=type_,
                amount=amount
            )
            session.add(new_code)
            session.commit()
            return new_code.id
        except Exception as e:
            session.rollback()
            print(f"Error creating discount code: {e}")
            return None
        finally:
            session.close()

    def get_discount_code(self, code):
        session = self.Session()
        try:
            return session.query(DiscountCode).filter(
                DiscountCode.code == code.upper(),
                DiscountCode.is_active == True
            ).first()
        except Exception as e:
            print(f"Error getting discount code: {e}")
            return None
        finally:
            session.close()

    def use_discount_code(self, code):
        session = self.Session()
        try:
            discount_code = session.query(DiscountCode).filter_by(code=code.upper()).first()
            if discount_code:
                discount_code.used_count += 1
                session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error using discount code: {e}")
        finally:
            session.close()

    # Logging methods
    def log_system(self, level, module, message, details=None):
        session = self.Session()
        try:
            new_log = SystemLog(
                level=level,
                module=module,
                message=message,
                details=json.dumps(details) if details else None
            )
            session.add(new_log)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error logging system event: {e}")
        finally:
            session.close()

    def log_error(self, error_type, error_message, traceback, user_id=None):
        session = self.Session()
        try:
            new_error = ErrorLog(
                error_type=error_type,
                error_message=error_message,
                traceback=traceback,
                user_id=user_id
            )
            session.add(new_error)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error logging error: {e}")
        finally:
            session.close()

    # Additional methods
    def get_user_by_id(self, user_id: int):
        session = self.Session()
        try:
            return session.query(User).get(user_id)
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
        finally:
            session.close()

    def get_service_by_id(self, service_id: int):
        session = self.Session()
        try:
            return session.query(Service).get(service_id)
        except Exception as e:
            print(f"Error getting service by ID: {e}")
            return None
        finally:
            session.close()