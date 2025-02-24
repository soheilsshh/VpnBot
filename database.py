import sqlite3
from datetime import datetime
import json

class Database:
    def __init__(self, db_path="data/vpn_bot.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    username TEXT,
                    wallet_balance REAL DEFAULT 0,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Services table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    price REAL,
                    duration INTEGER,
                    data_limit INTEGER,
                    is_active BOOLEAN DEFAULT 1,
                    inbound_id INTEGER
                )
            ''')
            
            # User services table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    service_id INTEGER,
                    marzban_username TEXT,
                    expire_date TIMESTAMP,
                    data_limit INTEGER,
                    data_used INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (service_id) REFERENCES services (id)
                )
            ''')
            
            # Transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    type TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Discount codes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discount_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE,
                    type TEXT,
                    amount REAL,
                    is_active BOOLEAN DEFAULT 1,
                    used_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # System logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    module TEXT,
                    message TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Error logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_type TEXT,
                    error_message TEXT,
                    traceback TEXT,
                    user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Reports table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    total_sales REAL,
                    total_transactions INTEGER,
                    new_users INTEGER,
                    active_services INTEGER,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Backups table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    size INTEGER,
                    type TEXT,
                    status TEXT,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    # User methods
    def create_user(self, telegram_id, username=None, is_admin=False):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR IGNORE INTO users (telegram_id, username, is_admin) VALUES (?, ?, ?)',
                (telegram_id, username, is_admin)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_user(self, telegram_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            return cursor.fetchone()
    
    def update_user_balance(self, telegram_id, amount):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET wallet_balance = wallet_balance + ? WHERE telegram_id = ?',
                (amount, telegram_id)
            )
            conn.commit()
    
    # Service methods
    def create_service(self, name, price, duration, data_limit, inbound_id=1):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO services (name, price, duration, data_limit, inbound_id) VALUES (?, ?, ?, ?, ?)',
                (name, price, duration, data_limit, inbound_id)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_active_services(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM services WHERE is_active = 1')
            return cursor.fetchall()
    
    def get_service(self, service_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
            return cursor.fetchone()
    
    # User service methods
    def create_user_service(self, user_id, service_id, marzban_username, expire_date, data_limit):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO user_services 
                   (user_id, service_id, marzban_username, expire_date, data_limit)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, service_id, marzban_username, expire_date, data_limit)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_user_active_services(self, user_id: int):
        """Get user's active services with service details"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    us.id,
                    us.user_id,
                    us.service_id,
                    us.marzban_username,
                    us.expire_date,
                    us.data_limit,
                    COALESCE(us.data_used, 0) as data_used,
                    us.is_active,
                    s.name,
                    s.price 
                FROM user_services us 
                JOIN services s ON us.service_id = s.id 
                WHERE us.user_id = ? AND us.is_active = 1
            ''', (user_id,))
            return cursor.fetchall()
    
    # Transaction methods
    def create_transaction(self, user_id, amount, type_, status='pending'):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO transactions (user_id, amount, type, status) VALUES (?, ?, ?, ?)',
                (user_id, amount, type_, status)
            )
            conn.commit()
            return cursor.lastrowid
    
    def update_transaction_status(self, transaction_id, status):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE transactions SET status = ? WHERE id = ?',
                (status, transaction_id)
            )
            conn.commit()
    
    # Discount code methods
    def create_discount_code(self, code, type_, amount):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO discount_codes (code, type, amount) VALUES (?, ?, ?)',
                (code.upper(), type_, amount)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_discount_code(self, code):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM discount_codes WHERE code = ? AND is_active = 1',
                (code.upper(),)
            )
            return cursor.fetchone()
    
    def use_discount_code(self, code):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE discount_codes SET used_count = used_count + 1 WHERE code = ?',
                (code.upper(),)
            )
            conn.commit()
    
    # Logging methods
    def log_system(self, level, module, message, details=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO system_logs (level, module, message, details) VALUES (?, ?, ?, ?)',
                (level, module, message, json.dumps(details) if details else None)
            )
            conn.commit()
    
    def log_error(self, error_type, error_message, traceback, user_id=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO error_logs (error_type, error_message, traceback, user_id) VALUES (?, ?, ?, ?)',
                (error_type, error_message, traceback, user_id)
            )
            conn.commit()

    def get_user_by_id(self, user_id: int):
        """Get user by database ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            return cursor.fetchone()

    def get_service_by_id(self, service_id: int):
        """Get service by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
            return cursor.fetchone()

    def create_user_service(self, user_id: int, service_id: int, marzban_username: str, expire_date: str, data_limit: int):
        """Create new user service"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO user_services 
                   (user_id, service_id, marzban_username, expire_date, data_limit)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, service_id, marzban_username, expire_date, data_limit)
            )
            conn.commit()
            return cursor.lastrowid 
