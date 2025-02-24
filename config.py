import os
from datetime import timedelta
import pytz

# Bot Configuration
BOT_TOKEN_MAIN = "7461887484:AAHui-Et2FGoqnCGvKgDcta422KZhg2x49c"
BOT_TOKEN = "7750358850:AAFU2uTCkiYlQTKHZT_fyFktk2xPI7-Elog"
ADMIN_ID_MAIN = 7403868937
ADMIN_ID = 5132040011
CHANNEL_ID_MAIN = -1002464583596
CHANNEL_ID = -1002176785577

# Marzban Panel Configuration
MARZBAN_CONFIG = {
    "username": "fartak",
    "password": "@Fartak#",
    "url": "https://bot.science-pdf.com:2087"
}

# Database Configuration
DATABASE_URL = "sqlite:///vpn_bot.db"

# Service Templates
SERVICE_TEMPLATES = {
    "basic": {
        "name": "سرویس پایه",
        "duration": 30,
        "data_limit": 50,
        "price": 100000,
        "inbound_id": 1
    },
    "premium": {
        "name": "سرویس ویژه",
        "duration": 90,
        "data_limit": 200,
        "price": 250000,
        "inbound_id": 1
    }
}

# Payment Settings
PAYMENT_METHODS = {
    "card": {
        "numbers": [
            "6037-9975-9874-5698",  # شماره کارت‌های شما
        ],
        "name": "فرتاک"  # نام صاحب کارت
    }
}

# Bot Settings
SUBSCRIPTION_REMINDER_DAYS = 3
SUBSCRIPTION_REMINDER_DATA = 5  # GB
TEST_ACCOUNT_SETTINGS = {
    "duration": 1,  # days
    "data_limit": 1  # GB
}

# Messages
MESSAGES = {
    "welcome": """
🌟 به ربات VPN خوش آمدید!
برای استفاده از خدمات، لطفا در کانال ما عضو شوید.
    """,
    "service_purchase": """
💫 سرویس {name} با موفقیت خریداری شد!
📅 تاریخ انقضا: {expire_date}
📊 حجم باقیمانده: {data_limit} GB
    """,
    "insufficient_balance": "موجودی کیف پول شما کافی نیست. لطفا ابتدا کیف پول خود را شارژ کنید.",
    "payment_received": "پرداخت شما با موفقیت انجام شد و کیف پول شما شارژ شد."
}

# Cleanup Settings
CLEANUP_SETTINGS = {
    "expired_users_days": 30,  # Delete expired users after 30 days
    "old_logs_days": 90,  # Delete logs older than 90 days
    "old_backups_days": 30,  # Delete backups older than 30 days
    "backup_retention_count": 10  # Keep last 10 backups minimum
}

# Performance Settings
PERFORMANCE_SETTINGS = {
    "max_concurrent_requests": 100,
    "request_timeout": 30,
    "connection_pool_size": 20,
    "max_connections": 1000
}

# Path Settings
PATH_SETTINGS = {
    "backup_dir": "backups",
    "log_dir": "logs",
    "temp_dir": "temp",
    "cache_dir": "cache"
}

# Timezone
TIMEZONE = pytz.timezone('Asia/Tehran') 