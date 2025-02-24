import os
from datetime import timedelta

# Cache Settings
CACHE_SETTINGS = {
    "enabled": True,
    "expire_time": 300,  # 5 minutes
    "max_size": 1000,  # Maximum number of items in cache
}

# Security Settings
SECURITY_SETTINGS = {
    "max_login_attempts": 3,
    "block_time": 1800,  # 30 minutes
    "required_membership": True,
    "invite_only": False,
    "allowed_protocols": ["vmess", "vless", "trojan", "shadowsocks"]
}

# Service Templates
SERVICE_TEMPLATES = {
    "basic": {
        "name": "سرویس پایه",
        "duration": 30,  # days
        "data_limit": 50,  # GB
        "price": 100000,  # Toman
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

# Notification Settings
NOTIFICATION_SETTINGS = {
    "expire_warning_days": [7, 3, 1],
    "data_warning_percent": [80, 90, 95],
    "admin_notifications": {
        "new_user": True,
        "new_purchase": True,
        "system_errors": True,
        "low_balance": True
    }
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

# Create required directories
for dir_path in PATH_SETTINGS.values():
    os.makedirs(dir_path, exist_ok=True) 